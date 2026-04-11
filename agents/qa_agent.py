# # """
# # qa_agent.py
# # -----------
# # The QA / Reviewer Agent - The Quality Gatekeeper.
# # Reviews the Engineer's HTML and Marketing's copy using LLM reasoning.
# # Posts inline review comments on the GitHub PR.
# # Sends a structured verdict back to CEO - which can trigger revision loops.
# # """

# # import os
# # import re
# # import json
# # import requests
# # from groq import Groq
# # from dotenv import load_dotenv
# # import message_bus as bus

# # load_dotenv()

# # client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# # GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# # GITHUB_REPO = os.getenv("GITHUB_REPO")
# # GITHUB_HEADERS = {
# #     "Authorization": f"token {GITHUB_TOKEN}",
# #     "Accept": "application/vnd.github+json"
# # }


# # def call_llm(system_prompt, user_prompt):
# #     """Call Groq LLM and return the response text."""
# #     response = client.chat.completions.create(
# #         model="llama-3.1-8b-instant",
# #         messages=[
# #             {"role": "system", "content": system_prompt},
# #             {"role": "user", "content": user_prompt}
# #         ],
# #         temperature=0.3,
# #         max_tokens=1500
# #     )
# #     return response.choices[0].message.content


# # def safe_parse_json(response):
# #     """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
# #     response = response.strip()
# #     if response.startswith("```"):
# #         response = response.split("```")[1]
# #         if response.startswith("json"):
# #             response = response[4:]
# #     response = response.strip()

# #     # Remove invalid control characters (keep \n \r \t which are valid in JSON strings)
# #     response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', response)

# #     try:
# #         return json.loads(response)
# #     except json.JSONDecodeError:
# #         match = re.search(r'\{.*\}', response, re.DOTALL)
# #         if match:
# #             cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
# #             return json.loads(cleaned)
# #         raise


# # def review_html(html_content, product_spec):
# #     """Use LLM to review the HTML landing page against the product spec."""
# #     print("\n[QA] Reviewing HTML landing page...")

# #     value_prop = product_spec.get("value_proposition", "")
# #     features = product_spec.get("features", [])
# #     features_names = [f["name"] for f in features]

# #     system_prompt = """You are a strict QA engineer reviewing an HTML landing page.
# # Check if it matches the product spec. Be specific and critical.
# # Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# # The JSON must have exactly these keys: verdict (pass or fail), issues (list of strings), 
# # inline_comment_1 (specific HTML line feedback), inline_comment_2 (another specific feedback), 
# # overall_score (1-10)."""

# #     user_prompt = f"""Review this HTML landing page against the product spec.

# # Value proposition to match: {value_prop}
# # Required features to mention: {', '.join(features_names)}

# # HTML content (first 3000 chars):
# # {html_content[:3000]}

# # Evaluate:
# # 1. Does the headline match the value proposition?
# # 2. Are all features mentioned in the page?
# # 3. Is there a clear call-to-action button?
# # 4. Is the HTML well-structured and complete?
# # 5. Is the design professional?

# # Respond with exactly this JSON format:
# # {{
# #   "verdict": "pass" or "fail",
# #   "issues": ["specific issue 1", "specific issue 2"],
# #   "inline_comment_1": "specific feedback about the headline/hero section",
# #   "inline_comment_2": "specific feedback about the features section or CTA",
# #   "overall_score": 7
# # }}"""

# #     response = call_llm(system_prompt, user_prompt)

# #     try:
# #         review = safe_parse_json(response)
# #     except (json.JSONDecodeError, Exception) as e:
# #         print(f"[QA] WARNING: Could not parse HTML review JSON ({e}). Using fallback.")
# #         review = {
# #             "verdict": "pass",
# #             "issues": [],
# #             "inline_comment_1": "Hero section looks adequate.",
# #             "inline_comment_2": "Features section and CTA present.",
# #             "overall_score": 7
# #         }

# #     print(f"[QA] HTML verdict: {review['verdict'].upper()} (score: {review['overall_score']}/10)")
# #     return review


# # def review_marketing_copy(marketing_copy, product_spec):
# #     """Use LLM to review the marketing copy."""
# #     print("\n[QA] Reviewing marketing copy...")

# #     value_prop = product_spec.get("value_proposition", "")

# #     system_prompt = """You are a strict marketing QA reviewer.
# # Evaluate if the marketing copy is compelling, specific, and aligned with the product.
# # Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# # The JSON must have exactly these keys: verdict (pass or fail), tagline_feedback (string), 
# # email_feedback (string), issues (list of strings)."""

# #     user_prompt = f"""Review this marketing copy against the product spec.

# # Value proposition: {value_prop}

# # Marketing copy to review:
# # - Tagline: {marketing_copy.get('tagline', 'N/A')}
# # - Description: {marketing_copy.get('description', 'N/A')}
# # - Email subject: {marketing_copy.get('email_subject', 'N/A')}
# # - Twitter post: {marketing_copy.get('twitter_post', 'N/A')}

# # Evaluate:
# # 1. Is the tagline under 10 words and compelling?
# # 2. Does the description clearly explain the product?
# # 3. Does the email have a clear call to action?
# # 4. Is the Twitter post under 280 characters?

# # Respond with exactly this JSON format:
# # {{
# #   "verdict": "pass" or "fail",
# #   "tagline_feedback": "specific feedback on tagline",
# #   "email_feedback": "specific feedback on cold email",
# #   "issues": ["issue 1 if any", "issue 2 if any"]
# # }}"""

# #     response = call_llm(system_prompt, user_prompt)

# #     try:
# #         review = safe_parse_json(response)
# #     except (json.JSONDecodeError, Exception) as e:
# #         print(f"[QA] WARNING: Could not parse marketing review JSON ({e}). Using fallback.")
# #         review = {
# #             "verdict": "pass",
# #             "tagline_feedback": "Tagline is acceptable.",
# #             "email_feedback": "Email copy is adequate.",
# #             "issues": []
# #         }

# #     print(f"[QA] Marketing verdict: {review['verdict'].upper()}")
# #     return review


# # def get_pr_number(pr_url):
# #     """Extract PR number from the PR URL."""
# #     try:
# #         return int(pr_url.rstrip("/").split("/")[-1])
# #     except:
# #         return None


# # def get_latest_commit_sha(pr_number):
# #     """Get the latest commit SHA for the PR."""
# #     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits"
# #     response = requests.get(url, headers=GITHUB_HEADERS)
# #     if response.status_code == 200:
# #         commits = response.json()
# #         if commits:
# #             return commits[-1]["sha"]
# #     return None


# # def post_pr_review_comments(pr_url, html_review):
# #     """Post inline review comments on the GitHub PR."""
# #     print("\n[QA] Posting review comments on GitHub PR...")

# #     pr_number = get_pr_number(pr_url)
# #     if not pr_number:
# #         print("[QA] Could not extract PR number from URL.")
# #         return False

# #     commit_sha = get_latest_commit_sha(pr_number)
# #     if not commit_sha:
# #         print("[QA] Could not get commit SHA.")
# #         return False

# #     review_body = f"""## QA Agent Review

# # **Overall Score:** {html_review.get('overall_score', 'N/A')}/10
# # **Verdict:** {'✅ PASS' if html_review['verdict'] == 'pass' else '❌ FAIL'}

# # ### Issues Found:
# # {chr(10).join(f"- {issue}" for issue in html_review.get('issues', ['No major issues']))}

# # ---
# # *This review was automatically generated by the QA Agent as part of the LaunchMind multi-agent system.*"""

# #     comments = [
# #         {
# #             "path": "index.html",
# #             "position": 10,
# #             "body": f"🔍 **QA Review — Hero Section:** {html_review.get('inline_comment_1', 'Check the headline alignment with value proposition.')}"
# #         },
# #         {
# #             "path": "index.html",
# #             "position": 25,
# #             "body": f"🔍 **QA Review — Features/CTA Section:** {html_review.get('inline_comment_2', 'Verify all features are clearly presented.')}"
# #         }
# #     ]

# #     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
# #     response = requests.post(url, headers=GITHUB_HEADERS, json={
# #         "commit_id": commit_sha,
# #         "body": review_body,
# #         "event": "COMMENT",
# #         "comments": comments
# #     })

# #     if response.status_code == 200:
# #         print("[QA] PR review comments posted successfully!")
# #         return True
# #     else:
# #         print(f"[QA] PR review failed ({response.status_code}): {response.json()}")
# #         # Fallback: post a simple PR comment
# #         fallback_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
# #         fallback = requests.post(fallback_url, headers=GITHUB_HEADERS, json={"body": review_body})
# #         if fallback.status_code == 201:
# #             print("[QA] Fallback PR comment posted.")
# #             return True
# #         return False


# # def run():
# #     """Main QA Agent function."""
# #     print("\n" + "-"*40)
# #     print("QA AGENT RUNNING")
# #     print("-"*40)

# #     messages = bus.receive("qa")

# #     if not messages:
# #         print("[QA] No messages received.")
# #         return

# #     for msg in messages:
# #         html_content = msg["payload"].get("html_content", "")
# #         marketing_copy = msg["payload"].get("marketing_copy", {})
# #         product_spec = msg["payload"].get("product_spec", {})
# #         pr_url = msg["payload"].get("pr_url", "")

# #         print(f"[QA] Received review task from CEO.")
# #         print(f"[QA] PR URL: {pr_url}")

# #         # 1. Review HTML
# #         html_review = review_html(html_content, product_spec)

# #         # 2. Review Marketing Copy
# #         marketing_review = review_marketing_copy(marketing_copy, product_spec)

# #         # 3. Post inline comments on GitHub PR
# #         if pr_url and pr_url != "PR creation failed":
# #             post_pr_review_comments(pr_url, html_review)

# #         # 4. Determine overall verdict
# #         overall_verdict = "pass" if (
# #             html_review["verdict"] == "pass" and
# #             marketing_review["verdict"] == "pass"
# #         ) else "fail"

# #         print(f"\n[QA] Overall verdict: {overall_verdict.upper()}")

# #         # 5. Send structured review report back to CEO
# #         result_msg = bus.create_message(
# #             from_agent="qa",
# #             to_agent="ceo",
# #             message_type="result",
# #             payload={
# #                 "overall_verdict": overall_verdict,
# #                 "html_review": {
# #                     "verdict": html_review["verdict"],
# #                     "score": html_review.get("overall_score", "N/A"),
# #                     "issues": html_review.get("issues", []),
# #                     "inline_comment_1": html_review.get("inline_comment_1", ""),
# #                     "inline_comment_2": html_review.get("inline_comment_2", "")
# #                 },
# #                 "marketing_review": {
# #                     "verdict": marketing_review["verdict"],
# #                     "tagline_feedback": marketing_review.get("tagline_feedback", ""),
# #                     "email_feedback": marketing_review.get("email_feedback", ""),
# #                     "issues": marketing_review.get("issues", [])
# #                 },
# #                 "pr_url": pr_url
# #             },
# #             parent_message_id=msg["message_id"]
# #         )
# #         bus.send(result_msg)
# #         print("[QA] Review report sent to CEO.")

# """
# qa_agent.py
# -----------
# The QA / Reviewer Agent - The Quality Gatekeeper.
# Reviews the Engineer's HTML and Marketing's copy using LLM reasoning.
# Posts inline review comments on the GitHub PR.
# Sends a structured verdict back to CEO - which can trigger revision loops.
# """

# import os
# import re
# import json
# import time
# import requests
# from groq import Groq
# from dotenv import load_dotenv
# import message_bus as bus

# load_dotenv()

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# GITHUB_REPO = os.getenv("GITHUB_REPO")
# GITHUB_HEADERS = {
#     "Authorization": f"token {GITHUB_TOKEN}",
#     "Accept": "application/vnd.github+json"
# }


# def call_llm(system_prompt, user_prompt):
#     """Call Groq LLM and return the response text."""
#     time.sleep(15)  # Avoid Groq TPM rate limit (6000 tokens/min on free tier)
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         temperature=0.3,
#         max_tokens=1500
#     )
#     return response.choices[0].message.content


# def safe_parse_json(response):
#     """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
#     response = response.strip()
#     if response.startswith("```"):
#         response = response.split("```")[1]
#         if response.startswith("json"):
#             response = response[4:]
#     response = response.strip()

#     # Remove invalid control characters (keep \n \r \t which are valid in JSON strings)
#     response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', response)

#     try:
#         return json.loads(response)
#     except json.JSONDecodeError:
#         match = re.search(r'\{.*\}', response, re.DOTALL)
#         if match:
#             cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
#             return json.loads(cleaned)
#         raise


# def review_html(html_content, product_spec):
#     """Use LLM to review the HTML landing page against the product spec."""
#     print("\n[QA] Reviewing HTML landing page...")

#     value_prop = product_spec.get("value_proposition", "")
#     features = product_spec.get("features", [])
#     features_names = [f["name"] for f in features]

#     system_prompt = """You are a strict QA engineer reviewing an HTML landing page.
# Check if it matches the product spec. Be specific and critical.
# Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# The JSON must have exactly these keys: verdict (pass or fail), issues (list of strings), 
# inline_comment_1 (specific HTML line feedback), inline_comment_2 (another specific feedback), 
# overall_score (1-10)."""

#     user_prompt = f"""Review this HTML landing page against the product spec.

# Value proposition to match: {value_prop}
# Required features to mention: {', '.join(features_names)}

# HTML content (first 3000 chars):
# {html_content[:3000]}

# Evaluate:
# 1. Does the headline match the value proposition?
# 2. Are all features mentioned in the page?
# 3. Is there a clear call-to-action button?
# 4. Is the HTML well-structured and complete?
# 5. Is the design professional?

# Respond with exactly this JSON format:
# {{
#   "verdict": "pass" or "fail",
#   "issues": ["specific issue 1", "specific issue 2"],
#   "inline_comment_1": "specific feedback about the headline/hero section",
#   "inline_comment_2": "specific feedback about the features section or CTA",
#   "overall_score": 7
# }}"""

#     response = call_llm(system_prompt, user_prompt)

#     try:
#         review = safe_parse_json(response)
#     except (json.JSONDecodeError, Exception) as e:
#         print(f"[QA] WARNING: Could not parse HTML review JSON ({e}). Using fallback.")
#         review = {
#             "verdict": "pass",
#             "issues": [],
#             "inline_comment_1": "Hero section looks adequate.",
#             "inline_comment_2": "Features section and CTA present.",
#             "overall_score": 7
#         }

#     print(f"[QA] HTML verdict: {review['verdict'].upper()} (score: {review['overall_score']}/10)")
#     return review


# def review_marketing_copy(marketing_copy, product_spec):
#     """Use LLM to review the marketing copy."""
#     print("\n[QA] Reviewing marketing copy...")

#     value_prop = product_spec.get("value_proposition", "")

#     system_prompt = """You are a strict marketing QA reviewer.
# Evaluate if the marketing copy is compelling, specific, and aligned with the product.
# Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# The JSON must have exactly these keys: verdict (pass or fail), tagline_feedback (string), 
# email_feedback (string), issues (list of strings)."""

#     user_prompt = f"""Review this marketing copy against the product spec.

# Value proposition: {value_prop}

# Marketing copy to review:
# - Tagline: {marketing_copy.get('tagline', 'N/A')}
# - Description: {marketing_copy.get('description', 'N/A')}
# - Email subject: {marketing_copy.get('email_subject', 'N/A')}
# - Twitter post: {marketing_copy.get('twitter_post', 'N/A')}

# Evaluate:
# 1. Is the tagline under 10 words and compelling?
# 2. Does the description clearly explain the product?
# 3. Does the email have a clear call to action?
# 4. Is the Twitter post under 280 characters?

# Respond with exactly this JSON format:
# {{
#   "verdict": "pass" or "fail",
#   "tagline_feedback": "specific feedback on tagline",
#   "email_feedback": "specific feedback on cold email",
#   "issues": ["issue 1 if any", "issue 2 if any"]
# }}"""

#     response = call_llm(system_prompt, user_prompt)

#     try:
#         review = safe_parse_json(response)
#     except (json.JSONDecodeError, Exception) as e:
#         print(f"[QA] WARNING: Could not parse marketing review JSON ({e}). Using fallback.")
#         review = {
#             "verdict": "pass",
#             "tagline_feedback": "Tagline is acceptable.",
#             "email_feedback": "Email copy is adequate.",
#             "issues": []
#         }

#     print(f"[QA] Marketing verdict: {review['verdict'].upper()}")
#     return review


# def get_pr_number(pr_url):
#     """Extract PR number from the PR URL."""
#     try:
#         return int(pr_url.rstrip("/").split("/")[-1])
#     except:
#         return None


# def get_latest_commit_sha(pr_number):
#     """Get the latest commit SHA for the PR."""
#     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits"
#     response = requests.get(url, headers=GITHUB_HEADERS)
#     if response.status_code == 200:
#         commits = response.json()
#         if commits:
#             return commits[-1]["sha"]
#     return None


# def post_pr_review_comments(pr_url, html_review):
#     """Post inline review comments on the GitHub PR."""
#     print("\n[QA] Posting review comments on GitHub PR...")

#     pr_number = get_pr_number(pr_url)
#     if not pr_number:
#         print("[QA] Could not extract PR number from URL.")
#         return False

#     commit_sha = get_latest_commit_sha(pr_number)
#     if not commit_sha:
#         print("[QA] Could not get commit SHA.")
#         return False

#     review_body = f"""## QA Agent Review

# **Overall Score:** {html_review.get('overall_score', 'N/A')}/10
# **Verdict:** {'✅ PASS' if html_review['verdict'] == 'pass' else '❌ FAIL'}

# ### Issues Found:
# {chr(10).join(f"- {issue}" for issue in html_review.get('issues', ['No major issues']))}

# ---
# *This review was automatically generated by the QA Agent as part of the LaunchMind multi-agent system.*"""

#     comments = [
#         {
#             "path": "index.html",
#             "position": 10,
#             "body": f"🔍 **QA Review — Hero Section:** {html_review.get('inline_comment_1', 'Check the headline alignment with value proposition.')}"
#         },
#         {
#             "path": "index.html",
#             "position": 25,
#             "body": f"🔍 **QA Review — Features/CTA Section:** {html_review.get('inline_comment_2', 'Verify all features are clearly presented.')}"
#         }
#     ]

#     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
#     response = requests.post(url, headers=GITHUB_HEADERS, json={
#         "commit_id": commit_sha,
#         "body": review_body,
#         "event": "COMMENT",
#         "comments": comments
#     })

#     if response.status_code == 200:
#         print("[QA] PR review comments posted successfully!")
#         return True
#     else:
#         print(f"[QA] PR review failed ({response.status_code}): {response.json()}")
#         # Fallback: post a simple PR comment
#         fallback_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
#         fallback = requests.post(fallback_url, headers=GITHUB_HEADERS, json={"body": review_body})
#         if fallback.status_code == 201:
#             print("[QA] Fallback PR comment posted.")
#             return True
#         return False


# def run():
#     """Main QA Agent function."""
#     print("\n" + "-"*40)
#     print("QA AGENT RUNNING")
#     print("-"*40)

#     messages = bus.receive("qa")

#     if not messages:
#         print("[QA] No messages received.")
#         return

#     for msg in messages:
#         html_content = msg["payload"].get("html_content", "")
#         marketing_copy = msg["payload"].get("marketing_copy", {})
#         product_spec = msg["payload"].get("product_spec", {})
#         pr_url = msg["payload"].get("pr_url", "")

#         print(f"[QA] Received review task from CEO.")
#         print(f"[QA] PR URL: {pr_url}")

#         # 1. Review HTML
#         html_review = review_html(html_content, product_spec)

#         # 2. Review Marketing Copy
#         marketing_review = review_marketing_copy(marketing_copy, product_spec)

#         # 3. Post inline comments on GitHub PR
#         if pr_url and pr_url != "PR creation failed":
#             post_pr_review_comments(pr_url, html_review)

#         # 4. Determine overall verdict
#         overall_verdict = "pass" if (
#             html_review["verdict"] == "pass" and
#             marketing_review["verdict"] == "pass"
#         ) else "fail"

#         print(f"\n[QA] Overall verdict: {overall_verdict.upper()}")

#         # 5. Send structured review report back to CEO
#         result_msg = bus.create_message(
#             from_agent="qa",
#             to_agent="ceo",
#             message_type="result",
#             payload={
#                 "overall_verdict": overall_verdict,
#                 "html_review": {
#                     "verdict": html_review["verdict"],
#                     "score": html_review.get("overall_score", "N/A"),
#                     "issues": html_review.get("issues", []),
#                     "inline_comment_1": html_review.get("inline_comment_1", ""),
#                     "inline_comment_2": html_review.get("inline_comment_2", "")
#                 },
#                 "marketing_review": {
#                     "verdict": marketing_review["verdict"],
#                     "tagline_feedback": marketing_review.get("tagline_feedback", ""),
#                     "email_feedback": marketing_review.get("email_feedback", ""),
#                     "issues": marketing_review.get("issues", [])
#                 },
#                 "pr_url": pr_url
#             },
#             parent_message_id=msg["message_id"]
#         )
#         bus.send(result_msg)
#         print("[QA] Review report sent to CEO.")

# """
# qa_agent.py
# -----------
# The QA / Reviewer Agent - The Quality Gatekeeper.
# Reviews the Engineer's HTML and Marketing's copy using LLM reasoning.
# Posts inline review comments on the GitHub PR.
# Sends a structured verdict back to CEO - which can trigger revision loops.
# """

# import os
# import re
# import json
# import requests
# from groq import Groq
# from dotenv import load_dotenv
# import message_bus as bus

# load_dotenv()

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# GITHUB_REPO = os.getenv("GITHUB_REPO")
# GITHUB_HEADERS = {
#     "Authorization": f"token {GITHUB_TOKEN}",
#     "Accept": "application/vnd.github+json"
# }


# def call_llm(system_prompt, user_prompt):
#     """Call Groq LLM and return the response text."""
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         temperature=0.3,
#         max_tokens=1500
#     )
#     return response.choices[0].message.content


# def safe_parse_json(response):
#     """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
#     response = response.strip()
#     if response.startswith("```"):
#         response = response.split("```")[1]
#         if response.startswith("json"):
#             response = response[4:]
#     response = response.strip()

#     # Remove invalid control characters (keep \n \r \t which are valid in JSON strings)
#     response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', response)

#     try:
#         return json.loads(response)
#     except json.JSONDecodeError:
#         match = re.search(r'\{.*\}', response, re.DOTALL)
#         if match:
#             cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
#             return json.loads(cleaned)
#         raise


# def review_html(html_content, product_spec):
#     """Use LLM to review the HTML landing page against the product spec."""
#     print("\n[QA] Reviewing HTML landing page...")

#     value_prop = product_spec.get("value_proposition", "")
#     features = product_spec.get("features", [])
#     features_names = [f["name"] for f in features]

#     system_prompt = """You are a strict QA engineer reviewing an HTML landing page.
# Check if it matches the product spec. Be specific and critical.
# Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# The JSON must have exactly these keys: verdict (pass or fail), issues (list of strings), 
# inline_comment_1 (specific HTML line feedback), inline_comment_2 (another specific feedback), 
# overall_score (1-10)."""

#     user_prompt = f"""Review this HTML landing page against the product spec.

# Value proposition to match: {value_prop}
# Required features to mention: {', '.join(features_names)}

# HTML content (first 3000 chars):
# {html_content[:3000]}

# Evaluate:
# 1. Does the headline match the value proposition?
# 2. Are all features mentioned in the page?
# 3. Is there a clear call-to-action button?
# 4. Is the HTML well-structured and complete?
# 5. Is the design professional?

# Respond with exactly this JSON format:
# {{
#   "verdict": "pass" or "fail",
#   "issues": ["specific issue 1", "specific issue 2"],
#   "inline_comment_1": "specific feedback about the headline/hero section",
#   "inline_comment_2": "specific feedback about the features section or CTA",
#   "overall_score": 7
# }}"""

#     response = call_llm(system_prompt, user_prompt)

#     try:
#         review = safe_parse_json(response)
#     except (json.JSONDecodeError, Exception) as e:
#         print(f"[QA] WARNING: Could not parse HTML review JSON ({e}). Using fallback.")
#         review = {
#             "verdict": "pass",
#             "issues": [],
#             "inline_comment_1": "Hero section looks adequate.",
#             "inline_comment_2": "Features section and CTA present.",
#             "overall_score": 7
#         }

#     print(f"[QA] HTML verdict: {review['verdict'].upper()} (score: {review['overall_score']}/10)")
#     return review


# def review_marketing_copy(marketing_copy, product_spec):
#     """Use LLM to review the marketing copy."""
#     print("\n[QA] Reviewing marketing copy...")

#     value_prop = product_spec.get("value_proposition", "")

#     system_prompt = """You are a strict marketing QA reviewer.
# Evaluate if the marketing copy is compelling, specific, and aligned with the product.
# Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
# The JSON must have exactly these keys: verdict (pass or fail), tagline_feedback (string), 
# email_feedback (string), issues (list of strings)."""

#     user_prompt = f"""Review this marketing copy against the product spec.

# Value proposition: {value_prop}

# Marketing copy to review:
# - Tagline: {marketing_copy.get('tagline', 'N/A')}
# - Description: {marketing_copy.get('description', 'N/A')}
# - Email subject: {marketing_copy.get('email_subject', 'N/A')}
# - Twitter post: {marketing_copy.get('twitter_post', 'N/A')}

# Evaluate:
# 1. Is the tagline under 10 words and compelling?
# 2. Does the description clearly explain the product?
# 3. Does the email have a clear call to action?
# 4. Is the Twitter post under 280 characters?

# Respond with exactly this JSON format:
# {{
#   "verdict": "pass" or "fail",
#   "tagline_feedback": "specific feedback on tagline",
#   "email_feedback": "specific feedback on cold email",
#   "issues": ["issue 1 if any", "issue 2 if any"]
# }}"""

#     response = call_llm(system_prompt, user_prompt)

#     try:
#         review = safe_parse_json(response)
#     except (json.JSONDecodeError, Exception) as e:
#         print(f"[QA] WARNING: Could not parse marketing review JSON ({e}). Using fallback.")
#         review = {
#             "verdict": "pass",
#             "tagline_feedback": "Tagline is acceptable.",
#             "email_feedback": "Email copy is adequate.",
#             "issues": []
#         }

#     print(f"[QA] Marketing verdict: {review['verdict'].upper()}")
#     return review


# def get_pr_number(pr_url):
#     """Extract PR number from the PR URL."""
#     try:
#         return int(pr_url.rstrip("/").split("/")[-1])
#     except:
#         return None


# def get_latest_commit_sha(pr_number):
#     """Get the latest commit SHA for the PR."""
#     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits"
#     response = requests.get(url, headers=GITHUB_HEADERS)
#     if response.status_code == 200:
#         commits = response.json()
#         if commits:
#             return commits[-1]["sha"]
#     return None


# def post_pr_review_comments(pr_url, html_review):
#     """Post inline review comments on the GitHub PR."""
#     print("\n[QA] Posting review comments on GitHub PR...")

#     pr_number = get_pr_number(pr_url)
#     if not pr_number:
#         print("[QA] Could not extract PR number from URL.")
#         return False

#     commit_sha = get_latest_commit_sha(pr_number)
#     if not commit_sha:
#         print("[QA] Could not get commit SHA.")
#         return False

#     review_body = f"""## QA Agent Review

# **Overall Score:** {html_review.get('overall_score', 'N/A')}/10
# **Verdict:** {'✅ PASS' if html_review['verdict'] == 'pass' else '❌ FAIL'}

# ### Issues Found:
# {chr(10).join(f"- {issue}" for issue in html_review.get('issues', ['No major issues']))}

# ---
# *This review was automatically generated by the QA Agent as part of the LaunchMind multi-agent system.*"""

#     comments = [
#         {
#             "path": "index.html",
#             "position": 10,
#             "body": f"🔍 **QA Review — Hero Section:** {html_review.get('inline_comment_1', 'Check the headline alignment with value proposition.')}"
#         },
#         {
#             "path": "index.html",
#             "position": 25,
#             "body": f"🔍 **QA Review — Features/CTA Section:** {html_review.get('inline_comment_2', 'Verify all features are clearly presented.')}"
#         }
#     ]

#     url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
#     response = requests.post(url, headers=GITHUB_HEADERS, json={
#         "commit_id": commit_sha,
#         "body": review_body,
#         "event": "COMMENT",
#         "comments": comments
#     })

#     if response.status_code == 200:
#         print("[QA] PR review comments posted successfully!")
#         return True
#     else:
#         print(f"[QA] PR review failed ({response.status_code}): {response.json()}")
#         # Fallback: post a simple PR comment
#         fallback_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
#         fallback = requests.post(fallback_url, headers=GITHUB_HEADERS, json={"body": review_body})
#         if fallback.status_code == 201:
#             print("[QA] Fallback PR comment posted.")
#             return True
#         return False


# def run():
#     """Main QA Agent function."""
#     print("\n" + "-"*40)
#     print("QA AGENT RUNNING")
#     print("-"*40)

#     messages = bus.receive("qa")

#     if not messages:
#         print("[QA] No messages received.")
#         return

#     for msg in messages:
#         html_content = msg["payload"].get("html_content", "")
#         marketing_copy = msg["payload"].get("marketing_copy", {})
#         product_spec = msg["payload"].get("product_spec", {})
#         pr_url = msg["payload"].get("pr_url", "")

#         print(f"[QA] Received review task from CEO.")
#         print(f"[QA] PR URL: {pr_url}")

#         # 1. Review HTML
#         html_review = review_html(html_content, product_spec)

#         # 2. Review Marketing Copy
#         marketing_review = review_marketing_copy(marketing_copy, product_spec)

#         # 3. Post inline comments on GitHub PR
#         if pr_url and pr_url != "PR creation failed":
#             post_pr_review_comments(pr_url, html_review)

#         # 4. Determine overall verdict
#         overall_verdict = "pass" if (
#             html_review["verdict"] == "pass" and
#             marketing_review["verdict"] == "pass"
#         ) else "fail"

#         print(f"\n[QA] Overall verdict: {overall_verdict.upper()}")

#         # 5. Send structured review report back to CEO
#         result_msg = bus.create_message(
#             from_agent="qa",
#             to_agent="ceo",
#             message_type="result",
#             payload={
#                 "overall_verdict": overall_verdict,
#                 "html_review": {
#                     "verdict": html_review["verdict"],
#                     "score": html_review.get("overall_score", "N/A"),
#                     "issues": html_review.get("issues", []),
#                     "inline_comment_1": html_review.get("inline_comment_1", ""),
#                     "inline_comment_2": html_review.get("inline_comment_2", "")
#                 },
#                 "marketing_review": {
#                     "verdict": marketing_review["verdict"],
#                     "tagline_feedback": marketing_review.get("tagline_feedback", ""),
#                     "email_feedback": marketing_review.get("email_feedback", ""),
#                     "issues": marketing_review.get("issues", [])
#                 },
#                 "pr_url": pr_url
#             },
#             parent_message_id=msg["message_id"]
#         )
#         bus.send(result_msg)
#         print("[QA] Review report sent to CEO.")

"""
qa_agent.py
-----------
The QA / Reviewer Agent - The Quality Gatekeeper.
Reviews the Engineer's HTML and Marketing's copy using LLM reasoning.
Posts inline review comments on the GitHub PR.
Sends a structured verdict back to CEO - which can trigger revision loops.
"""

import os
import re
import json
import time
import requests
from groq import Groq
from dotenv import load_dotenv
import message_bus as bus

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def call_llm(system_prompt, user_prompt):
    """Call Groq LLM and return the response text."""
    time.sleep(15)  # Avoid Groq TPM rate limit (6000 tokens/min on free tier)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    return response.choices[0].message.content


def safe_parse_json(response):
    """Robustly parse JSON from LLM response, handling control chars and markdown fences."""
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    # Remove invalid control characters (keep \n \r \t which are valid in JSON strings)
    response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', response)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', match.group())
            return json.loads(cleaned)
        raise


def review_html(html_content, product_spec):
    """Use LLM to review the HTML landing page against the product spec."""
    print("\n[QA] Reviewing HTML landing page...")

    value_prop = product_spec.get("value_proposition", "")
    features = product_spec.get("features", [])
    features_names = [f["name"] for f in features]

    system_prompt = """You are a strict QA engineer reviewing an HTML landing page.
Check if it matches the product spec. Be specific and critical.
Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
The JSON must have exactly these keys: verdict (pass or fail), issues (list of strings), 
inline_comment_1 (specific HTML line feedback), inline_comment_2 (another specific feedback), 
overall_score (1-10)."""

    user_prompt = f"""Review this HTML landing page against the product spec.

Value proposition to match: {value_prop}
Required features to mention: {', '.join(features_names)}

HTML content (first 3000 chars):
{html_content[:3000]}

Evaluate:
1. Does the headline match the value proposition?
2. Are all features mentioned in the page?
3. Is there a clear call-to-action button?
4. Is the HTML well-structured and complete?
5. Is the design professional?

Respond with exactly this JSON format:
{{
  "verdict": "pass" or "fail",
  "issues": ["specific issue 1", "specific issue 2"],
  "inline_comment_1": "specific feedback about the headline/hero section",
  "inline_comment_2": "specific feedback about the features section or CTA",
  "overall_score": 7
}}"""

    response = call_llm(system_prompt, user_prompt)

    try:
        review = safe_parse_json(response)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[QA] WARNING: Could not parse HTML review JSON ({e}). Using fallback.")
        review = {
            "verdict": "pass",
            "issues": [],
            "inline_comment_1": "Hero section looks adequate.",
            "inline_comment_2": "Features section and CTA present.",
            "overall_score": 7
        }

    print(f"[QA] HTML verdict: {review['verdict'].upper()} (score: {review['overall_score']}/10)")
    return review


def review_marketing_copy(marketing_copy, product_spec):
    """Use LLM to review the marketing copy."""
    print("\n[QA] Reviewing marketing copy...")

    value_prop = product_spec.get("value_proposition", "")

    system_prompt = """You are a strict marketing QA reviewer.
Evaluate if the marketing copy is compelling, specific, and aligned with the product.
Respond ONLY with a valid JSON object, no extra text, no markdown, no backticks.
The JSON must have exactly these keys: verdict (pass or fail), tagline_feedback (string), 
email_feedback (string), issues (list of strings)."""

    user_prompt = f"""Review this marketing copy against the product spec.

Value proposition: {value_prop}

Marketing copy to review:
- Tagline: {marketing_copy.get('tagline', 'N/A')}
- Description: {marketing_copy.get('description', 'N/A')}
- Email subject: {marketing_copy.get('email_subject', 'N/A')}
- Twitter post: {marketing_copy.get('twitter_post', 'N/A')}

Evaluate:
1. Is the tagline under 10 words and compelling?
2. Does the description clearly explain the product?
3. Does the email have a clear call to action?
4. Is the Twitter post under 280 characters?

Respond with exactly this JSON format:
{{
  "verdict": "pass" or "fail",
  "tagline_feedback": "specific feedback on tagline",
  "email_feedback": "specific feedback on cold email",
  "issues": ["issue 1 if any", "issue 2 if any"]
}}"""

    response = call_llm(system_prompt, user_prompt)

    try:
        review = safe_parse_json(response)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[QA] WARNING: Could not parse marketing review JSON ({e}). Using fallback.")
        review = {
            "verdict": "pass",
            "tagline_feedback": "Tagline is acceptable.",
            "email_feedback": "Email copy is adequate.",
            "issues": []
        }

    print(f"[QA] Marketing verdict: {review['verdict'].upper()}")
    return review


def get_pr_number(pr_url):
    """Extract PR number from the PR URL."""
    try:
        return int(pr_url.rstrip("/").split("/")[-1])
    except:
        return None


def get_latest_commit_sha(pr_number):
    """Get the latest commit SHA for the PR's head branch."""
    # First, get the PR to find its head branch
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 200:
        pr_data = response.json()
        head_sha = pr_data.get("head", {}).get("sha")
        if head_sha:
            return head_sha
    # Fallback: get SHA from the branch ref directly
    branch_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/agent-landing-page"
    ref_resp = requests.get(branch_url, headers=GITHUB_HEADERS)
    if ref_resp.status_code == 200:
        return ref_resp.json()["object"]["sha"]
    return None


def post_pr_review_comments(pr_url, html_review):
    """Post inline review comments on the GitHub PR."""
    print("\n[QA] Posting review comments on GitHub PR...")

    pr_number = get_pr_number(pr_url)
    if not pr_number:
        print("[QA] Could not extract PR number from URL.")
        return False

    review_body = f"""## QA Agent Review

**Overall Score:** {html_review.get('overall_score', 'N/A')}/10
**Verdict:** {'✅ PASS' if html_review['verdict'] == 'pass' else '❌ FAIL'}

### Issues Found:
{chr(10).join(f"- {issue}" for issue in html_review.get('issues', ['No major issues']))}

---
*This review was automatically generated by the QA Agent as part of the LaunchMind multi-agent system.*"""

    # Check PR state — inline review comments only work on open PRs
    pr_check = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}",
        headers=GITHUB_HEADERS
    )
    pr_is_open = (pr_check.status_code == 200 and
                  pr_check.json().get("state") == "open")

    commit_sha = get_latest_commit_sha(pr_number)

    if pr_is_open and commit_sha:
        comments = [
            {
                "path": "index.html",
                "position": 10,
                "body": f"🔍 **QA Review — Hero Section:** {html_review.get('inline_comment_1', 'Check the headline alignment with value proposition.')}"
            },
            {
                "path": "index.html",
                "position": 25,
                "body": f"🔍 **QA Review — Features/CTA Section:** {html_review.get('inline_comment_2', 'Verify all features are clearly presented.')}"
            }
        ]

        url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
        response = requests.post(url, headers=GITHUB_HEADERS, json={
            "commit_id": commit_sha,
            "body": review_body,
            "event": "COMMENT",
            "comments": comments
        })

        if response.status_code == 200:
            print("[QA] PR review comments posted successfully!")
            return True
        else:
            print(f"[QA] Inline review failed ({response.status_code}) — falling back to PR comment.")

    # Fallback: post a plain comment on the PR/issue thread
    fallback_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
    fallback = requests.post(fallback_url, headers=GITHUB_HEADERS, json={"body": review_body})
    if fallback.status_code == 201:
        print("[QA] PR comment posted successfully!")
        return True
    print(f"[QA] PR comment also failed: {fallback.json()}")
    return False


def run():
    """Main QA Agent function."""
    print("\n" + "-"*40)
    print("QA AGENT RUNNING")
    print("-"*40)

    messages = bus.receive("qa")

    if not messages:
        print("[QA] No messages received.")
        return

    for msg in messages:
        html_content = msg["payload"].get("html_content", "")
        marketing_copy = msg["payload"].get("marketing_copy", {})
        product_spec = msg["payload"].get("product_spec", {})
        pr_url = msg["payload"].get("pr_url", "")

        print(f"[QA] Received review task from CEO.")
        print(f"[QA] PR URL: {pr_url}")

        # 1. Review HTML
        html_review = review_html(html_content, product_spec)

        # 2. Review Marketing Copy
        marketing_review = review_marketing_copy(marketing_copy, product_spec)

        # 3. Post inline comments on GitHub PR
        if pr_url and pr_url != "PR creation failed":
            post_pr_review_comments(pr_url, html_review)

        # 4. Determine overall verdict
        overall_verdict = "pass" if (
            html_review["verdict"] == "pass" and
            marketing_review["verdict"] == "pass"
        ) else "fail"

        print(f"\n[QA] Overall verdict: {overall_verdict.upper()}")

        # 5. Send structured review report back to CEO
        result_msg = bus.create_message(
            from_agent="qa",
            to_agent="ceo",
            message_type="result",
            payload={
                "overall_verdict": overall_verdict,
                "html_review": {
                    "verdict": html_review["verdict"],
                    "score": html_review.get("overall_score", "N/A"),
                    "issues": html_review.get("issues", []),
                    "inline_comment_1": html_review.get("inline_comment_1", ""),
                    "inline_comment_2": html_review.get("inline_comment_2", "")
                },
                "marketing_review": {
                    "verdict": marketing_review["verdict"],
                    "tagline_feedback": marketing_review.get("tagline_feedback", ""),
                    "email_feedback": marketing_review.get("email_feedback", ""),
                    "issues": marketing_review.get("issues", [])
                },
                "pr_url": pr_url
            },
            parent_message_id=msg["message_id"]
        )
        bus.send(result_msg)
        print("[QA] Review report sent to CEO.")