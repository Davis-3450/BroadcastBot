import os
import time
import json
import logging
from openai import OpenAI
from instagrapi import Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_env_var(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ValueError(f"Environment variable {name} is required.")
    return value

def get_reference_content(path):
    if not path:
        return ""

    if not os.path.exists(path):
        logger.warning(f"Reference document not found at {path}")
        return ""

    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.json'):
                data = json.load(f)
                return json.dumps(data, indent=2)
            else:
                return f.read()
    except Exception as e:
        logger.error(f"Error reading reference document: {e}")
        return ""

def generate_message(client, model, reference_content, prompt_template):
    system_prompt = "You are a helpful assistant that generates interesting messages."
    if reference_content:
        system_prompt += f"\n\nReference Material:\n{reference_content}"

    user_content = prompt_template or "Generate a new message for the broadcast channel."

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        return None

def broadcast_message(cl, target_id, message):
    try:
        # Convert target_id to int if possible, as thread_ids are usually ints
        try:
            thread_id = int(target_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid target ID format: {target_id}. Must be an integer.")
            return False

        cl.direct_send(message, thread_ids=[thread_id])
        logger.info("Message broadcasted successfully.")
        return True
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        return False

def main():
    try:
        # Load configuration
        api_key = get_env_var("OPENAI_API_KEY", required=True)
        model = get_env_var("OPENAI_MODEL", "gpt-4o")

        ig_user = get_env_var("IG_USERNAME", required=True)
        ig_pass = get_env_var("IG_PASSWORD", required=True)
        ig_target_id = get_env_var("IG_TARGET_ID", required=True)

        ref_doc_path = get_env_var("REFERENCE_DOC_PATH")
        # Default interval to 1 hour
        interval = int(get_env_var("BROADCAST_INTERVAL", 3600))
        prompt_template = get_env_var("PROMPT_TEMPLATE")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    # Initialize clients
    openai_client = OpenAI(api_key=api_key)
    ig_client = Client()

    # IG Login
    try:
        logger.info(f"Logging in as {ig_user}...")
        ig_client.login(ig_user, ig_pass)
        logger.info("Logged in successfully.")
    except Exception as e:
        logger.error(f"Failed to login to Instagram: {e}")
        return

    logger.info("Bot started.")

    while True:
        try:
            logger.info("Generating message...")
            ref_content = get_reference_content(ref_doc_path)
            message = generate_message(openai_client, model, ref_content, prompt_template)

            if message:
                logger.info(f"Generated message: {message[:50]}...")
                success = broadcast_message(ig_client, ig_target_id, message)
                if not success:
                    logger.warning("Failed to broadcast message.")
            else:
                logger.warning("Failed to generate message.")

            logger.info(f"Sleeping for {interval} seconds...")
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            logger.info(f"Sleeping for {interval} seconds before retrying...")
            time.sleep(interval)

if __name__ == "__main__":
    main()
