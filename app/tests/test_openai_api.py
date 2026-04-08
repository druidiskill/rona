import os
import unittest

from dotenv import load_dotenv


load_dotenv()


class TestOpenAIApi(unittest.TestCase):
    def test_openai_api_key_is_optional_for_import(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.skipTest("OPENAI_API_KEY is not set")

        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        self.assertIsNotNone(client)


if __name__ == "__main__":
    unittest.main()
