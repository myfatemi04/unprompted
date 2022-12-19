from .backends import openai


def _split_into_parts(template: str):
	import re

	# Adding parentheses also returns the delimiter that was matched
	return re.split(r"(\{[^\{\}]+\})", template)

class Prompt:
	"""
	You specify a skeleton for the prompt, and where variables can be inserted with `{}`.
	You can specify existing values for variables with keyword arguments. Any unspecified
	values will be filled in by GPT-3.

	Right now, this API supports three variable types:
	 - `line`: value is generated by GPT-3 until the `\\n` character is encountered (one newline).
	 - `multiline`: value is generated by GPT-3 until the `\\n\\n` sequence is encountered (two newlines).
	 - `list of [min-max]`: values are generated by GPT-3 as a bulleted list, repeating until at least `min` values are
	 	present and clipping after `max` values are found.
	"""
	def __init__(self, template: str):
		self.template = template

	def __call__(self, **input_values):
		current_string = ""
		output_values = {}
		removed_last_trailing_space = False
		for part in _split_into_parts(self.template):
			is_variable = part.startswith("{") and part.endswith("}")
			
			if not is_variable:
				# If the current_string ends with the prefix to `part`, then merge them.

				overlap_length = 1
				while (overlap_length < len(part) and overlap_length < len(current_string)) and (current_string[-overlap_length:] == part[:overlap_length]):
					overlap_length += 1

				current_string += part[overlap_length - 1:]
				continue

			# It is a variable
			variable_spec = part[1:-1]
			list_min = 0
			list_max = 0
			if ':' not in variable_spec:
				variable_name = variable_spec
				variable_type = "line"
			else:
				variable_name, variable_type = variable_spec.split(":")
				# variable_type can be 'line', 'multiline', or 'list of (min)-(max)'
				variable_type = variable_type.strip()
				if variable_type.startswith("list of "):
					try:
						count_range = variable_type[len('list of '):]
						if "-" in count_range:
							list_min_str, list_max_str = count_range.split("-")
							list_min = int(list_min_str)
							list_max = int(list_max_str)
						else:
							list_min = list_max = int(count_range)
					except:
						raise ValueError("Error parsing variable descriptor: " + variable_type)

					variable_type = 'list'
				else:
					assert variable_type in ["line", "multiline", "wait"]
			
			if variable_name in input_values:
				# Stringify the variable
				if variable_type == 'list':
					if not current_string.endswith("\n"):
						print("WARNING: Lists must start on their own line. Automatically adding a newline.")
						current_string += '\n'
					for item in input_values[variable_name]:
						current_string += ' - ' + item + '\n'
				else:
					current_string += str(input_values[variable_name])
				
				continue

			if variable_type == 'wait':
				# variable is not found in inputs, and we are told to wait for it
				return current_string, output_values

			if variable_type == 'list':
				# Requires multiple prompts for one variable
				list_results = []
				# Force at least list_min results
				while len(list_results) < list_min:
					result = " -" + openai("text-davinci-003", current_string + " -", stop='\n\n')
					result_lines = result.split("\n")
					for line in result_lines:
						if len(list_results) == list_max:
							break
						if line.startswith(" -"):
							list_results.append(line[2:].strip())
							# Standardize list format
							current_string += " - " + line[2:].strip() + "\n"
						else:
							break
				# For the last bit, 
				output_values[variable_name] = list_results
				continue

			if variable_type == 'multiline':
				stop = '\n\n'
			elif variable_type == 'line':
				stop = '\n'
			else:
				stop = None
			
			try:
				result = openai("text-davinci-003", current_string, stop=stop)
			except Exception as e:
				print(f"ERROR: {e}. Settings: {{ {variable_name=}, {variable_type=}, {stop=} }}")
				raise e

			if not result:
				print(f"WARNING: No completion generated. Settings: {{ {variable_type=}, {stop=} }}. Note: It is possible that the model predicted the stop sequence ({repr(stop)}) as the beginning of the completion.")

			if removed_last_trailing_space and result.startswith(" "):
				output_values[variable_name] = result[1:]
			else:
				output_values[variable_name] = result

			current_string += result

		return current_string, output_values

if __name__ == '__main__':
	from .backends import set_api_key
	import os

	set_api_key(os.environ['OPENAI_API_KEY'])

	prompt = Prompt("""
Today, we are announcing a new invention: the {invention_name}!

Here are some of its capabilities:
{capabilities: list of 3-5}

Motto of the invention: "{motto}"

Some hashtags to share this on social media:
{hashtags: list of 4}
""".strip())

	completion, values = prompt(invention_name="self-solving Rubik's Cube")
	print(completion)