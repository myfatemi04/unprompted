import requests

_openai_api_key = None

def set_api_key(key):
	global _openai_api_key

	_openai_api_key = key

def openai(model_name, prompt: str, temperature=0.7, max_tokens=120, stop=None) -> str:
	if _openai_api_key is None:
		raise ValueError("OpenAI API key has not been set. Please set one with `prompting.backends.set_api_key(key)`.")

	body = {
		'model': model_name,
		'prompt': prompt,
		'temperature': temperature,
		'max_tokens': max_tokens,
		'top_p': 1,
		'frequency_penalty': 0,
		'presence_penalty': 0,
		'stop': stop,
	}
	headers = {
		'Authorization': 'Bearer ' + _openai_api_key,
		'Content-Type': 'application/json',
	}
	response = requests.post('https://api.openai.com/v1/completions', json=body, headers=headers)
	response = response.json()

	if 'choices' not in response:
		raise ValueError("Invalid response from OpenAI: " + str(response))

	return response['choices'][0]['text']
