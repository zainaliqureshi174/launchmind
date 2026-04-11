"""
app.py
------
Flask backend for LaunchMind UI.
Runs the agent pipeline in a background thread, streams live logs
to the browser via Server-Sent Events, and handles HITL pause/resume.

Usage:
    pip install flask flask-cors
    python app.py
Then open launchmind_ui.html in your browser (or visit http://localhost:5000)
"""

import sys
import os
import json
import queue
import threading
import time
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so agents can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder='.')
CORS(app)

# ── Shared state ─────────────────────────────────────────────────────────────

# SSE log queue — pipeline pushes events, /stream sends them to browser
log_queue = queue.Queue()

# HITL gate — pipeline blocks on this event waiting for human decision
hitl_event = threading.Event()
hitl_decision = {'value': None}   # 'approve' | 'reject'

# Pipeline state
pipeline_state = {
    'running': False,
    'agents': {
        'ceo':       'idle',
        'product':   'idle',
        'engineer':  'idle',
        'marketing': 'idle',
        'qa':        'idle',
    },
    'metrics': {'msgs': 0, 'llm': 0, 'loops': 0, 'hitl': 0},
    'hitl_mode': False,
    'hitl_waiting': False,
    'hitl_payload': None,
    'hitl_agent': None,
}


# ── SSE helpers ───────────────────────────────────────────────────────────────

def push(event_type, data):
    """Push a structured SSE event into the queue."""
    log_queue.put({'type': event_type, 'data': data})


def push_log(text, tag='SYS', level='sys'):
    push('log', {'text': text, 'tag': tag, 'level': level})


def push_agent(agent_id, state, badge):
    pipeline_state['agents'][agent_id] = state
    push('agent', {'id': agent_id, 'state': state, 'badge': badge})


def push_metrics():
    push('metrics', pipeline_state['metrics'])


def push_msg(from_a, to_a, msg_type, msg_id):
    pipeline_state['metrics']['msgs'] += 1
    push_metrics()
    push('message', {'from': from_a, 'to': to_a, 'type': msg_type, 'id': msg_id})
    push_log(f'[BUS] {from_a} → {to_a} | type={msg_type} | id={msg_id[:8]}', 'BUS', 'bus')


def push_llm(agent, purpose):
    pipeline_state['metrics']['llm'] += 1
    push_metrics()
    push_log(f'{agent}: {purpose}', 'LLM', 'llm')


def push_hitl(agent, payload_text):
    pipeline_state['metrics']['hitl'] += 1
    pipeline_state['hitl_waiting'] = True
    pipeline_state['hitl_agent'] = agent
    pipeline_state['hitl_payload'] = payload_text
    push_metrics()
    push('hitl', {'agent': agent, 'payload': payload_text})
    push_log(f'HITL gate — waiting for human decision on {agent} output.', 'HITL', 'warn')


# ── HITL gate ─────────────────────────────────────────────────────────────────

def wait_for_human(agent, payload_text):
    """
    Block the pipeline thread until the human clicks Approve or Reject.
    Returns 'approve' or 'reject'.
    """
    hitl_event.clear()
    hitl_decision['value'] = None
    push_hitl(agent, payload_text)
    hitl_event.wait()          # blocks here until /decision is called
    pipeline_state['hitl_waiting'] = False
    return hitl_decision['value']


# ── Monkey-patch message_bus to push events ───────────────────────────────────

def patch_message_bus():
    import message_bus as bus

    original_send = bus.send
    def patched_send(message):
        original_send(message)
        push_msg(
            message['from_agent'],
            message['to_agent'],
            message['message_type'],
            message['message_id']
        )
    bus.send = patched_send

    original_create = bus.create_message
    def patched_create(from_agent, to_agent, message_type, payload, parent_message_id=None):
        msg = original_create(from_agent, to_agent, message_type, payload, parent_message_id)
        return msg
    bus.create_message = patched_create


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline(idea, hitl_mode):
    """
    Runs in a background thread.
    Calls the real agents but intercepts key moments for HITL gates.
    """
    pipeline_state['running'] = True
    pipeline_state['hitl_mode'] = hitl_mode
    pipeline_state['metrics'] = {'msgs': 0, 'llm': 0, 'loops': 0, 'hitl': 0}

    # Reset all agents to idle
    for a in pipeline_state['agents']:
        push_agent(a, 'waiting', 'IDLE')

    push('status', {'running': True})
    push_log('Pipeline initiated.', 'SYS', 'ok')
    push_log(f'Idea: "{idea[:100]}{"..." if len(idea)>100 else ""}"', 'SYS', 'sys')
    push_log(f'HITL mode: {"ENABLED" if hitl_mode else "DISABLED"}', 'SYS', 'warn' if hitl_mode else 'sys')

    try:
        patch_message_bus()
        import message_bus as bus

        # ── STEP 1: CEO decomposes idea ──────────────────────────────────────
        push_agent('ceo', 'running', 'RUNNING')
        push_log('CEO Agent initializing...', 'CEO', 'sys')
        push_llm('CEO', 'decompose startup idea → task assignments for sub-agents')

        from agents.ceo_agent import decompose_idea, review_output
        tasks = decompose_idea(idea)

        push_log(f'CEO: tasks generated for product, engineer, marketing.', 'CEO', 'sys')

        # ── STEP 2: Product Agent ────────────────────────────────────────────
        product_msg = bus.create_message('ceo', 'product', 'task', {'idea': idea, 'task': tasks['product_task']})
        bus.send(product_msg)

        push_agent('product', 'running', 'RUNNING')
        push_log('Product Agent received task. Generating product specification...', 'PROD', 'sys')
        push_llm('PRODUCT', 'generate product spec → value_proposition, personas, features[5], user_stories[3]')

        from agents.product_agent import generate_product_spec
        spec = generate_product_spec(idea, tasks['product_task'])

        push_log(f'Product: spec generated — {len(spec.get("personas",[]))} personas, {len(spec.get("features",[]))} features.', 'PROD', 'sys')

        result_msg = bus.create_message('product', 'ceo', 'result', spec, product_msg['message_id'])
        bus.send(result_msg)

        confirm_msg = bus.create_message('product', 'ceo', 'confirmation',
            {'status': 'Product spec ready', 'spec_keys': list(spec.keys())}, product_msg['message_id'])
        bus.send(confirm_msg)

        # CEO reviews product spec
        push_llm('CEO', 'review product spec — evaluating completeness and specificity')
        review = review_output('product', spec, tasks['product_task'])
        push_log(f'CEO review verdict: {review["verdict"].upper()} — {review["reason"]}',
                 'CEO', 'ok' if review['verdict']=='pass' else 'warn')

        # HITL gate for product
        if hitl_mode:
            payload_text = (
                f"value_proposition: {spec.get('value_proposition','')}\n\n"
                f"personas: {json.dumps(spec.get('personas',[]), indent=2)}\n\n"
                f"features: {json.dumps([f['name'] for f in spec.get('features',[])], indent=2)}\n\n"
                f"user_stories: {json.dumps(spec.get('user_stories',[]), indent=2)}\n\n"
                f"CEO verdict: {review['verdict'].upper()} — {review['reason']}"
            )
            decision = wait_for_human('Product Agent', payload_text)
            if decision == 'reject':
                pipeline_state['metrics']['loops'] += 1
                push_metrics()
                rev_msg = bus.create_message('ceo', 'product', 'revision_request',
                    {'idea': idea, 'task': tasks['product_task'], 'feedback': review.get('feedback', 'Improve specificity.')},
                    product_msg['message_id'])
                bus.send(rev_msg)
                push_agent('product', 'running', 'RUNNING')
                push_log('Product Agent processing revision...', 'PROD', 'warn')
                push_llm('PRODUCT', 'revise spec based on human + CEO feedback')
                spec = generate_product_spec(idea, tasks['product_task'], review.get('feedback'))
                push_log('Product: revised spec ready.', 'PROD', 'ok')
                bus.send(bus.create_message('product', 'ceo', 'result', spec, rev_msg['message_id']))
        elif review['verdict'] == 'fail':
            pipeline_state['metrics']['loops'] += 1
            push_metrics()
            rev_msg = bus.create_message('ceo', 'product', 'revision_request',
                {'idea': idea, 'task': tasks['product_task'], 'feedback': review.get('feedback', '')},
                product_msg['message_id'])
            bus.send(rev_msg)
            push_agent('product', 'running', 'RUNNING')
            push_log('CEO triggered automatic revision for product spec.', 'CEO', 'warn')
            push_llm('PRODUCT', 'revise spec based on CEO feedback')
            spec = generate_product_spec(idea, tasks['product_task'], review.get('feedback'))
            push_log('Product: revised spec ready.', 'PROD', 'ok')
            bus.send(bus.create_message('product', 'ceo', 'result', spec, rev_msg['message_id']))

        push_agent('product', 'done', 'DONE')
        push_log('Product Agent task complete.', 'PROD', 'ok')

        # ── STEP 3: Engineer Agent ───────────────────────────────────────────
        eng_msg = bus.create_message('ceo', 'engineer', 'task',
            {'idea': idea, 'task': tasks['engineer_task'], 'product_spec': spec})
        bus.send(eng_msg)

        push_agent('engineer', 'running', 'RUNNING')
        push_log('Engineer Agent received spec. Starting build sequence...', 'ENG', 'sys')
        push_llm('ENGINEER', 'generate complete HTML landing page with inline CSS, features section, CTA')

        from agents.engineer_agent import generate_html, create_github_issue, get_main_branch_sha, create_branch, commit_file, create_pull_request
        html_content = generate_html(idea, spec)
        push_log('Engineer: HTML generated.', 'ENG', 'sys')

        issue_url = create_github_issue(idea, spec)
        push_log(f'Engineer: GitHub issue created → {issue_url or "failed"}', 'ENG', 'ok' if issue_url else 'err')

        base_sha = get_main_branch_sha()
        branch_name = 'agent-landing-page'
        create_branch(branch_name, base_sha)
        push_log(f'Engineer: branch "{branch_name}" ready.', 'ENG', 'sys')

        commit_file(branch_name, html_content, idea)
        push_log('Engineer: index.html committed (author: EngineerAgent <agent@launchmind.ai>).', 'ENG', 'sys')

        pr_url = create_pull_request(branch_name, idea, issue_url)
        push_log(f'Engineer: PR opened → {pr_url or "failed"}', 'ENG', 'ok' if pr_url else 'err')

        if hitl_mode:
            payload_text = (
                f"GitHub Issue: {issue_url}\n"
                f"Branch: {branch_name}\n"
                f"PR URL: {pr_url}\n\n"
                f"HTML Preview (first 500 chars):\n{html_content[:500]}..."
            )
            decision = wait_for_human('Engineer Agent', payload_text)
            if decision == 'reject':
                pipeline_state['metrics']['loops'] += 1
                push_metrics()
                rev_eng = bus.create_message('ceo', 'engineer', 'revision_request',
                    {'idea': idea, 'task': tasks['engineer_task'], 'product_spec': spec,
                     'feedback': 'Improve HTML quality and feature coverage.'}, eng_msg['message_id'])
                bus.send(rev_eng)
                push_agent('engineer', 'running', 'RUNNING')
                push_log('Engineer Agent processing revision...', 'ENG', 'warn')
                push_llm('ENGINEER', 'revise HTML based on human feedback')
                html_content = generate_html(idea, spec)
                commit_file(branch_name, html_content, idea)
                push_log('Engineer: revised HTML committed.', 'ENG', 'ok')
                bus.send(bus.create_message('engineer', 'ceo', 'result',
                    {'pr_url': pr_url, 'issue_url': issue_url, 'branch': branch_name,
                     'html_generated': True, 'html_content': html_content}, rev_eng['message_id']))

        eng_result = bus.create_message('engineer', 'ceo', 'result',
            {'pr_url': pr_url or 'PR creation failed', 'issue_url': issue_url or 'failed',
             'branch': branch_name, 'html_generated': True, 'html_content': html_content},
            eng_msg['message_id'])
        bus.send(eng_result)
        push_agent('engineer', 'done', 'DONE')
        push_log('Engineer Agent task complete.', 'ENG', 'ok')

        # ── STEP 4: Marketing Agent ──────────────────────────────────────────
        mkt_msg = bus.create_message('ceo', 'marketing', 'task',
            {'idea': idea, 'task': tasks['marketing_task'], 'product_spec': spec, 'pr_url': pr_url or ''})
        bus.send(mkt_msg)

        push_agent('marketing', 'running', 'RUNNING')
        push_log('Marketing Agent received spec + PR URL. Generating copy...', 'MKT', 'sys')
        push_llm('MARKETING', 'generate tagline, email subject+body, twitter, linkedin, instagram')

        from agents.marketing_agent import generate_marketing_copy, send_email, post_to_slack
        copy = generate_marketing_copy(idea, spec)
        push_log(f'Marketing: tagline → "{copy.get("tagline","")}"', 'MKT', 'sys')

        email_sent = send_email(copy)
        push_log(f'Marketing: email {"sent — 202 Accepted" if email_sent else "FAILED"}.', 'MKT', 'ok' if email_sent else 'err')

        slack_posted = post_to_slack(idea, copy, pr_url or '')
        push_log(f'Marketing: Slack Block Kit message {"posted" if slack_posted else "FAILED"}.', 'MKT', 'ok' if slack_posted else 'err')

        if hitl_mode:
            payload_text = (
                f"tagline: {copy.get('tagline','')}\n"
                f"description: {copy.get('description','')}\n\n"
                f"email_subject: {copy.get('email_subject','')}\n"
                f"email_sent: {email_sent}\n\n"
                f"twitter_post: {copy.get('twitter_post','')}\n"
                f"linkedin_post: {copy.get('linkedin_post','')}\n"
                f"instagram_post: {copy.get('instagram_post','')}\n\n"
                f"slack_posted: {slack_posted}"
            )
            decision = wait_for_human('Marketing Agent', payload_text)
            if decision == 'reject':
                pipeline_state['metrics']['loops'] += 1
                push_metrics()
                rev_mkt = bus.create_message('ceo', 'marketing', 'revision_request',
                    {'idea': idea, 'task': tasks['marketing_task'], 'product_spec': spec,
                     'pr_url': pr_url or '', 'feedback': 'Improve tagline and email copy.'}, mkt_msg['message_id'])
                bus.send(rev_mkt)
                push_agent('marketing', 'running', 'RUNNING')
                push_log('Marketing Agent processing revision...', 'MKT', 'warn')
                push_llm('MARKETING', 'revise copy based on human feedback')
                copy = generate_marketing_copy(idea, spec)
                email_sent = send_email(copy)
                slack_posted = post_to_slack(idea, copy, pr_url or '')
                push_log('Marketing: revised copy sent.', 'MKT', 'ok')
                bus.send(bus.create_message('marketing', 'ceo', 'result', {
                    **{k: copy.get(k,'') for k in ['tagline','description','email_subject','twitter_post','linkedin_post','instagram_post']},
                    'email_sent': email_sent, 'slack_posted': slack_posted}, rev_mkt['message_id']))

        mkt_result = bus.create_message('marketing', 'ceo', 'result', {
            **{k: copy.get(k,'') for k in ['tagline','description','email_subject','twitter_post','linkedin_post','instagram_post']},
            'email_sent': email_sent, 'slack_posted': slack_posted}, mkt_msg['message_id'])
        bus.send(mkt_result)
        bus.send(bus.create_message('marketing', 'ceo', 'confirmation',
            {'status': 'Marketing complete', 'email_sent': email_sent, 'slack_posted': slack_posted},
            mkt_msg['message_id']))
        push_agent('marketing', 'done', 'DONE')
        push_log('Marketing Agent task complete.', 'MKT', 'ok')

        # ── STEP 5: QA Agent ─────────────────────────────────────────────────
        qa_msg = bus.create_message('ceo', 'qa', 'task',
            {'html_content': html_content, 'marketing_copy': copy,
             'product_spec': spec, 'pr_url': pr_url or ''})
        bus.send(qa_msg)

        push_agent('qa', 'running', 'RUNNING')
        push_log('QA Agent received HTML + marketing copy. Starting review...', 'QA', 'sys')
        push_llm('QA', 'review HTML — headline alignment, feature coverage, CTA presence, structure')

        from agents.qa_agent import review_html, review_marketing_copy, post_pr_review_comments
        html_review = review_html(html_content, spec)
        push_log(f'QA HTML verdict: {html_review["verdict"].upper()} (score: {html_review.get("overall_score","?")}/10)', 'QA', 'ok' if html_review['verdict']=='pass' else 'warn')

        push_llm('QA', 'review marketing copy — tagline, email CTA, twitter length')
        mkt_review = review_marketing_copy(copy, spec)
        push_log(f'QA Marketing verdict: {mkt_review["verdict"].upper()}', 'QA', 'ok' if mkt_review['verdict']=='pass' else 'warn')

        if pr_url and pr_url != 'PR creation failed':
            post_pr_review_comments(pr_url, html_review)
            push_log('QA: inline PR review comments posted (2 comments on index.html).', 'QA', 'ok')

        overall = 'pass' if html_review['verdict']=='pass' and mkt_review['verdict']=='pass' else 'fail'
        push_log(f'QA overall verdict: {overall.upper()}', 'QA', 'ok' if overall=='pass' else 'err')

        if hitl_mode:
            payload_text = (
                f"html_review:\n"
                f"  verdict: {html_review['verdict'].upper()}\n"
                f"  score: {html_review.get('overall_score','?')}/10\n"
                f"  issues: {html_review.get('issues',[])}\n"
                f"  comment_1: {html_review.get('inline_comment_1','')}\n"
                f"  comment_2: {html_review.get('inline_comment_2','')}\n\n"
                f"marketing_review:\n"
                f"  verdict: {mkt_review['verdict'].upper()}\n"
                f"  tagline_feedback: {mkt_review.get('tagline_feedback','')}\n"
                f"  email_feedback: {mkt_review.get('email_feedback','')}\n\n"
                f"overall_verdict: {overall.upper()}\n"
                f"pr_comments_posted: true"
            )
            wait_for_human('QA Agent', payload_text)

        qa_result = bus.create_message('qa', 'ceo', 'result', {
            'overall_verdict': overall,
            'html_review': {'verdict': html_review['verdict'], 'score': html_review.get('overall_score'), 'issues': html_review.get('issues',[])},
            'marketing_review': {'verdict': mkt_review['verdict']},
            'pr_url': pr_url or ''}, qa_msg['message_id'])
        bus.send(qa_result)
        push_agent('qa', 'done', 'DONE')
        push_log('QA Agent task complete.', 'QA', 'ok')

        # ── STEP 6: QA fail → Engineer revision ─────────────────────────────
        if overall == 'fail' and not hitl_mode:
            pipeline_state['metrics']['loops'] += 1
            push_metrics()
            issues = html_review.get('issues', [])
            feedback = '; '.join(issues) if issues else 'Improve HTML quality.'
            rev_eng2 = bus.create_message('ceo', 'engineer', 'revision_request',
                {'idea': idea, 'task': tasks['engineer_task'], 'product_spec': spec, 'feedback': feedback},
                eng_msg['message_id'])
            bus.send(rev_eng2)
            push_agent('engineer', 'running', 'RUNNING')
            push_log('CEO: QA failed — requesting Engineer revision.', 'CEO', 'warn')
            push_llm('ENGINEER', 'revise HTML based on QA issues')
            html_content = generate_html(idea, spec)
            commit_file(branch_name, html_content, idea)
            push_log('Engineer: revised HTML committed.', 'ENG', 'ok')
            push_agent('engineer', 'done', 'DONE')

        # ── STEP 7: Final Slack summary ───────────────────────────────────────
        push_agent('ceo', 'running', 'RUNNING')
        push_log('CEO: all results received. Posting final summary to Slack...', 'CEO', 'sys')

        from agents.ceo_agent import post_final_summary
        post_final_summary(idea,
            {'value_proposition': spec.get('value_proposition','')},
            {'pr_url': pr_url or 'N/A', 'issue_url': issue_url or 'N/A'},
            {'tagline': copy.get('tagline','N/A')},
            {'overall_verdict': overall})
        push_log('CEO: final summary posted to Slack #launches.', 'CEO', 'ok')
        push_agent('ceo', 'done', 'DONE')

        m = pipeline_state['metrics']
        push_log(f'Pipeline complete — {m["msgs"]} messages, {m["llm"]} LLM calls, {m["loops"]} revision loops.', 'SYS', 'ok')
        push('status', {'running': False, 'complete': True})

    except Exception as e:
        push_log(f'PIPELINE ERROR: {str(e)}', 'ERR', 'err')
        push('status', {'running': False, 'error': str(e)})
        for a in pipeline_state['agents']:
            if pipeline_state['agents'][a] == 'running':
                push_agent(a, 'fail', 'ERROR')
    finally:
        pipeline_state['running'] = False


# ── Flask Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'launchmind_ui.html')

@app.route('/run', methods=['POST'])
def run():
    if pipeline_state['running']:
        return jsonify({'error': 'Pipeline already running'}), 409
    data = request.get_json()
    idea = data.get('idea', '').strip()
    hitl_mode = data.get('hitl', False)
    if not idea:
        return jsonify({'error': 'No idea provided'}), 400

    # Clear the log queue
    while not log_queue.empty():
        try: log_queue.get_nowait()
        except: break

    # Start pipeline in background thread
    t = threading.Thread(target=run_pipeline, args=(idea, hitl_mode), daemon=True)
    t.start()
    return jsonify({'status': 'started'})


@app.route('/stream')
def stream():
    """Server-Sent Events endpoint — streams live events to browser."""
    def generate():
        yield 'data: {"type":"connected"}\n\n'
        while True:
            try:
                event = log_queue.get(timeout=30)
                yield f'data: {json.dumps(event)}\n\n'
            except queue.Empty:
                yield 'data: {"type":"ping"}\n\n'
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/decision', methods=['POST'])
def decision():
    """Human sends approve or reject for the current HITL gate."""
    if not pipeline_state['hitl_waiting']:
        return jsonify({'error': 'No HITL gate active'}), 400
    data = request.get_json()
    choice = data.get('decision')  # 'approve' or 'reject'
    if choice not in ('approve', 'reject'):
        return jsonify({'error': 'Invalid decision'}), 400
    hitl_decision['value'] = choice
    hitl_event.set()
    return jsonify({'status': 'decision received', 'decision': choice})


@app.route('/status')
def status():
    return jsonify({
        'running': pipeline_state['running'],
        'agents': pipeline_state['agents'],
        'metrics': pipeline_state['metrics'],
        'hitl_waiting': pipeline_state['hitl_waiting'],
        'hitl_agent': pipeline_state['hitl_agent'],
    })


if __name__ == '__main__':
    print('\n' + '='*50)
    print('  LaunchMind Flask Backend')
    print('='*50)
    print('  Open: http://localhost:5000')
    print('  API:  POST /run  |  GET /stream  |  POST /decision')
    print('='*50 + '\n')
    app.run(debug=False, threaded=True, port=5000)
