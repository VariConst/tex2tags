replaceable_environments = ["equation",
                            "subequations",
                            "eqnarray"]

replaceable_commands_with_braces = ["ref",
                                    "cite"]

import sys

def print_usage_and_exit(program_name):
    print("usage: {0} [-h | --help]\n" \
          "       {0} file.tex [file_tagged.tex]\n" \
          "       {0} file.tex --untag [file_tagged.tex]".format(program_name))
    exit()

def print_help_and_exit():
    # TODO: Help message
    print("help: ... ")
    exit()

def decompose_filename(filename):
    decomposed_name = filename.split(".")
    name = decomposed_name[0]
    extension = ""
    for ext in decomposed_name[1:]:
        extension += ".{0}".format(ext)

    return (name, extension)

# TODO: Fix encoding auto-selection, because e.g. on windows it chooses cp1251
def get_file_contents(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            file_contents = file.read()
    except(FileNotFoundError):
        print("File \"{0}\" not found!".format(filename))
        exit()

    return file_contents

# TODO: "x" mode? Or other way to protect against rewriting existing file?
def dump_into_file(filename, output):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(output)

class Token:
    def __init__(self, symbol="", content="", number=0):
        self.symbol = symbol
        self.content = content
        self.number = number

    def copy(self):
        copy_token = Token(self.symbol, self.content, self.number)
        return copy_token

class Stream:
    def __init__(self, content="", index=0):
        self.content = content
        self.size = len(self.content)
        self.index = index

    def load_file_contents(self, filename):
        self.content = get_file_contents(filename)
        self.size = len(self.content)
        self.index = 0

    def at(self):
        if (self.index < self.size):
            result = self.content[self.index]
        else:
            result = ""

        return result

    def advance(self, step=1):
        if ((self.index + step) < self.size):
            self.index += step
            result = self.at()
        else:
            self.index = self.size
            result = ""

        return result

    def backtrack(self, step=1):
        if ((self.index - step) >= 0):
            self.index -= step
        else:
            self.index = 0

        return self.at()

class Tagger:
    def __init__(self, replaceable_environments, replaceable_commands_with_braces):
        self.input_stream = Stream()
        self.output = ""
        self.replaceable_environments = replaceable_environments
        self.replaceable_commands_with_braces = replaceable_commands_with_braces

        self.prev_token_end_index = 0
        self.token_start_index = 0
        self.token = Token()
        self.trackable_tex_commands = ["begin", "end"] + self.replaceable_commands_with_braces

        self.tag_count = 0
        self.tags = {}

    def tag_tex_file(self, filename):
        self.input_stream.load_file_contents(filename)
        self.output = ""

        self.prev_token_end_index = 0
        self.token_start_index = 0
        self.token = Token()

        while self.input_stream.at():
            start = self.token_start_index
            start_token = self.token.copy()
            if not self.expect_replaceable():
                self.output += self.input_stream.content[start:self.token_start_index]
            else:
                tag_label = "<mt{0}>".format(self.tag_count)
                tag_content = self.input_stream.content[start:self.prev_token_end_index]
                self.tags[tag_label] = tag_content
                self.tag_count += 1

                self.output += tag_label
                self.output += self.input_stream.content[self.prev_token_end_index:self.token_start_index]

        return self.output

    def untag_tex_file(self, filename):
        self.input_stream.load_file_contents(filename)
        self.output = ""

        self.prev_token_end_index = 0
        self.token_start_index = 0
        self.token = Token()

        while self.input_stream.at():
            start = self.token_start_index
            start_token = self.token.copy()
            if not self.accept_tag():
                self.next_token()
                self.output += self.input_stream.content[start:self.token_start_index]
            else:
                tag_label = "<mt{0}>".format(self.tag_count)
                tag_content = self.tags[tag_label]
                self.output += tag_content
                self.output += self.input_stream.content[self.prev_token_end_index:self.token_start_index]

        return self.output

    # NOTE: Recursive descent parser
    # TODO: Take into account \verb+$$+ etc.
    # TODO: Take into account $a = b \text{where $a$ is ...}$ etc.
    def next_token(self):
        self.prev_token_end_index = self.input_stream.index
        while True:
            self.token_start_index = self.input_stream.index
            char = self.input_stream.at()
            self.token.content = char
            if (char.isalpha()):
                self.token.symbol = "identifier"
                while (self.input_stream.advance().isalpha()):
                    self.token.content += self.input_stream.at()

                break

            elif (char.isdigit()):
                self.token.symbol = "number"
                while (self.input_stream.advance().isdigit()):
                    self.token.content += self.input_stream.at()
                self.token.number = int(self.token.content)

                break

            elif (char == "\\"):
                if (self.input_stream.advance().isalpha()):
                    self.token.content += self.input_stream.at()
                    while (self.input_stream.advance().isalpha()):
                        self.token.content += self.input_stream.at()

                    command_match = False
                    for command in self.trackable_tex_commands:
                        if (self.token.content == ("\\" + command)):
                            self.token.symbol = command
                            command_match = True

                            break

                    if command_match:
                        break

                else:
                    self.input_stream.advance()

            elif ((char == "{") or
                  (char == "}") or
                  (char == "<") or
                  (char == ">")):
                self.token.symbol = char
                self.input_stream.advance()

                break

            elif (char == "$"):
                if (self.input_stream.advance() == "$"):
                    self.token.symbol = "$$"
                    self.token.content += self.input_stream.at()
                    self.input_stream.advance()
                else:
                    self.token.symbol = "$"

                break

            elif self.input_stream.at():
                self.input_stream.advance()

            else:
                self.token.symbol = "end_of_file"
                self.token.content = ""

                break

        return self.token

    def accept_symbol(self, expected):
        if (self.token.symbol == expected):
            self.next_token()
            return True

        return False

    def accept_one_of_symbols(self, expected):
        for symbol in expected:
            if self.accept_symbol(symbol):
                return True

        return False

    def expect_symbol(self, expected):
        if self.accept_symbol(expected):
            return True

        self.next_token()
        return False

    def expect_identifier(self, expected_identifier):
        token_content = self.token.content
        if self.expect_symbol("identifier"):
            if (token_content != expected_identifier):
                return False
        else:
            return False

        return True

    def accept_inline_math(self):
        if not self.accept_symbol("$"):
            return False

        while not self.expect_symbol("$"):
            continue

        return True

    def accept_display_math(self):
        if not self.accept_symbol("$$"):
            return False

        while not self.expect_symbol("$$"):
            if not self.input_stream.at():
                return False
            continue

        return True

    def accept_begin_end_environment(self):
        if not self.accept_symbol("begin"):
            return False

        if not self.accept_symbol("{"):
            return False

        token_content = self.token.content
        environment = ""
        if self.expect_symbol("identifier"):
            for env in self.replaceable_environments:
                if (token_content == env):
                    environment = env
                    break
            else:
                return False
        else:
            return False

        if not self.expect_symbol("}"):
            return False


        while True:
            if not self.expect_symbol("end"):
                continue

            if not self.accept_symbol("{"):
                continue

            if not self.expect_identifier(environment):
                continue

            if not self.expect_symbol("}"):
                continue

            return True

    def accept_command_with_braces(self):
        if not self.accept_one_of_symbols(self.replaceable_commands_with_braces):
            return False

        if not self.expect_symbol("{"):
            return False

        while not self.expect_symbol("}"):
            continue

        return True

    def expect_replaceable(self):
        if self.accept_inline_math():
            return True

        if self.accept_display_math():
            return True

        if self.accept_begin_end_environment():
            return True

        if self.accept_command_with_braces():
            return True

        self.next_token()
        return False

    def accept_tag(self):
        if not self.accept_symbol("<"):
            return False

        if not self.expect_identifier("mt"):
            return False

        if (self.token.symbol == "number"):
            self.tag_count = self.token.number
            self.next_token()
        else:
            return False

        if not self.expect_symbol(">"):
            return False

        return True

program_name = sys.argv[0]
args = sys.argv[1:]
args_count = len(args)
untag_requested = False
if ((args_count > 0) and (args_count < 4)):
    if ((args_count == 1) and
        ((args[0] == "-h") or
         (args[0] == "--help"))):
            print_help_and_exit()

    original_file_name = args[0]

    name, extension = decompose_filename(original_file_name)
    tagged_file_name = "{0}_tagged{1}".format(name, extension)
    untagged_file_name = "{0}_untagged{1}".format(name, extension)

    if (args_count == 2):
        if (args[1] == "--untag"):
            untag_requested = True
        else:
            tagged_file_name = args[1]
    elif (args_count == 3):
        if (args[1] != "--untag"):
            print_usage_and_exit(program_name)
        else:
            untag_requested = True
            tagged_file_name = args[2]

            name, extension = decompose_filename(tagged_file_name)
            untagged_file_name = "{0}_untagged{1}".format(name, extension)
else:
    print_usage_and_exit(program_name)

tagger = Tagger(replaceable_environments, replaceable_commands_with_braces)
tagged_output = tagger.tag_tex_file(original_file_name)

#for tag_label in tagger.tags:
#    print(tag_label + tagger.tags[tag_label])

# TODO: More differentiation with and without --untag flag? Like do not
# generate tagged_output if untagging or do not generate tags dict if tagging
# etc.
if not untag_requested:
    dump_into_file(tagged_file_name, tagged_output)
else:
    untagged_output = tagger.untag_tex_file(tagged_file_name)
    dump_into_file(untagged_file_name, untagged_output)

print("Done")
