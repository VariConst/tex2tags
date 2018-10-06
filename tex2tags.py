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
        self.trackable_tex_commands = ["begin", "end"] + self.replaceable_commands_with_braces

        self.token = Token()

        self.inside_replaceable = False
        self.replaceable = ""
        self.tags = {}

    def tag_tex_file(self, filename):
        self.input_stream.load_file_contents(filename)
        self.output = ""

        self.token = Token()

        self.inside_replaceable = False
        self.replaceable = ""
        self.tags = {}

        tag_count = 0
        while self.expect_replaceable():
            tag_label = "<mt{0}>".format(tag_count)
            tag_content = self.replaceable
            self.tags[tag_label] = tag_content

            self.output += tag_label

            self.inside_replaceable = False
            self.replaceable = ""
            tag_count += 1

        return self.output

    def untag_tex_file(self, filename):
        self.input_stream.load_file_contents(filename)
        self.output = ""

        self.token = Token()

        self.inside_replaceable = False
        self.replaceable = ""

        while self.expect_tag():
            self.inside_replaceable = False
            tag_label = self.replaceable
            tag_content = self.tags[tag_label]
            self.output += tag_content
            self.replaceable = ""

        return self.output

    # NOTE: Recursive descent parser
    # "accept" methods on fail do not advance position in input_stream and do
    # not change state inside_replaceable to False,
    # "expect" methods demand specific rule in place and on fail change state
    # inside_replaceable to False and advance input_stream
    # TODO: Take into account \verb+$$+ etc.
    # TODO: Take into account $a = b \text{where $a$ is ...}$ etc.
    def next_token(self):
        char = self.input_stream.at()
        self.token.content = char
        if (char.isalpha()):
            self.token.symbol = "identifier"
            while (self.input_stream.advance().isalpha()):
                self.token.content += self.input_stream.at()

        elif (char.isdigit()):
            self.token.symbol = "number"
            while (self.input_stream.advance().isdigit()):
                self.token.content += self.input_stream.at()
            self.token.number = int(self.token.content)

        elif (char == "\\"):
            if (self.input_stream.advance().isalpha()):
                self.token.content += self.input_stream.at()
                while (self.input_stream.advance().isalpha()):
                    self.token.content += self.input_stream.at()

                for command in self.trackable_tex_commands:
                    if (self.token.content == ("\\" + command)):
                        self.token.symbol = command

                        break

                else:
                    self.token.symbol = "other"

            else:
                self.token.symbol = "other"
                self.token.content += self.input_stream.at()
                self.input_stream.advance()

        elif ((char == "{") or
              (char == "}") or
              (char == "<") or
              (char == ">")):
            self.token.symbol = char
            self.input_stream.advance()

        elif (char == "$"):
            if (self.input_stream.advance() == "$"):
                self.token.symbol = "$$"
                self.token.content += self.input_stream.at()
                self.input_stream.advance()
            else:
                self.token.symbol = "$"

        elif self.input_stream.at():
            self.token.symbol = "other"
            self.input_stream.advance()

        else:
            self.token.symbol = "end_of_file"
            self.token.content = ""

        return self.token

    def consume_other_symbols(self):
        buffer = ""
        while (self.token.symbol == "other"):
            buffer += self.token.content
            self.next_token()

        if self.inside_replaceable:
            self.replaceable += buffer
        else:
            self.output += buffer

    def accept_symbol(self, expected):
        self.consume_other_symbols()

        if (self.token.symbol == expected):
            self.inside_replaceable = True
            self.replaceable += self.token.content
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

        self.inside_replaceable = False
        self.output += (self.replaceable + self.token.content)
        self.replaceable = ""
        self.next_token()

        return False

    def accept_identifier(self, expected_identifier):
        self.consume_other_symbols()

        if (self.token.content == expected_identifier):
            assert(self.token.symbol == "identifier")
            assert(self.inside_replaceable)

            self.replaceable += self.token.content
            self.next_token()

            return True

        return False

    def accept_one_of_identifiers(self, expected_identifiers):
        for ident in expected_identifiers:
            if self.accept_identifier(ident):
                return True

        return False

    def expect_identifier(self, expected_identifier):
        if self.accept_identifier(expected_identifier):
            return True

        self.inside_replaceable = False
        self.output += (self.replaceable + self.token.content)
        self.replaceable = ""
        self.next_token()

        return False

    def expect_one_of_identifiers(self, expected_identifiers):
        for ident in expected_identifiers:
            if self.accept_identifier(ident):
                return True

        self.inside_replaceable = False
        self.output += (self.replaceable + self.token.content)
        self.replaceable = ""
        self.next_token()

        return False

    def expect_begin_end_environment(self):
        assert(not self.inside_replaceable)

        if not self.expect_symbol("begin"):
            return False

        if not self.expect_symbol("{"):
            return False

        environment = self.token.content
        if not self.expect_one_of_identifiers(self.replaceable_environments):
            return False

        if not self.expect_symbol("}"):
            return False

        while True:
            if not self.accept_symbol("end"):
                self.replaceable += self.token.content
                self.next_token()
                continue

            if not self.expect_symbol("{"):
                continue

            if not self.accept_identifier(environment):
                self.replaceable += self.token.content
                self.next_token()
                continue

            if not self.expect_symbol("}"):
                continue

            return True

    def accept_inline_math(self):
        assert(not self.inside_replaceable)

        if not self.accept_symbol("$"):
            return False

        # TODO: Robustness: make ALL while loops terminate if the end of stream is
        # reached
        while not self.accept_symbol("$"):
            self.replaceable += self.token.content
            self.next_token()

        return True

    def accept_display_math(self):
        assert(not self.inside_replaceable)

        if not self.accept_symbol("$$"):
            return False

        assert(self.inside_replaceable)

        while not self.accept_symbol("$$"):
            self.replaceable += self.token.content
            self.next_token()

        return True

    def accept_command_with_braces(self):
        assert(not self.inside_replaceable)

        if not self.accept_one_of_symbols(self.replaceable_commands_with_braces):
            return False

        assert(self.inside_replaceable)

        if not self.expect_symbol("{"):
            return False

        while not self.accept_symbol("}"):
            self.replaceable += self.token.content
            self.next_token()

        return True

    def expect_replaceable(self):
        assert(not self.inside_replaceable)

        while True:
            while (self.token.symbol != "end_of_file"):
                if self.token.symbol not in (["begin", "$", "$$"] +
                                             self.replaceable_commands_with_braces):
                    self.output += self.token.content
                    self.next_token()
                else:
                    break
            else:
                return False

            if (self.token.symbol == "begin"):
                if self.expect_begin_end_environment():
                    return True
                else:
                    continue

            if self.accept_inline_math():
                return True

            if self.accept_display_math():
                return True

            if self.accept_command_with_braces():
                return True

    def expect_tag(self):
        assert(not self.inside_replaceable)

        while True:
            while (self.token.symbol != "end_of_file"):
                if self.expect_symbol("<"):
                    break
            else:
                return False

            if not self.expect_identifier("mt"):
                continue

            if not self.expect_symbol("number"):
                continue

            if self.expect_symbol(">"):
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
