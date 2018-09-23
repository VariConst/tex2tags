# TODO: Take into account \verb+$$+ etc.

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

class Stream:
    def __init__(self, content="", size=0, index=0):
        self.content = content
        self.size = size
        self.index = index

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

class Token:
    def __init__(self, symbol="", content="", number=0):
        self.symbol = symbol
        self.content = content
        self.number = number

def get_token(input):
    token = Token()
    char = input.at()
    if (char.isalpha()):
        token.symbol = "identifier"
        token.content += char
        while (input.advance().isalpha()):
            token.content += input.at()
    elif (char.isdigit()):
        token.symbol = "number"
        token.content += char
        while (input.advance().isdigit()):
            token.content += input.at()
        token.number = int(token.content)
    elif ((char == "\\") or
          (char == "{") or
          (char == "}") or
          (char == "<") or
          (char == ">") or
          (char == "*")):
        token.symbol = char
        token.content = token.symbol
        input.advance()
    elif (char == "$"):
        if (input.advance() == "$"):
            token.symbol = "$$"
            token.content = token.symbol
            input.advance()
        else:
            token.symbol = "$"
            token.content = token.symbol
    elif (char.isspace()):
        token.symbol = "space"
        token.content = char
        while(input.advance().isspace()):
            token.content += input.at()
    else:
        token.symbol = "other"
        token.content = char
        input.advance()

    return token

def get_significant_token(input):
    token = get_token(input)
    while ((token.symbol == "space") or
           (token.symbol == "other") or
           (token.symbol == "*")):
        token = get_token(input)

    return token

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

# TODO: Fix encoding auto-selection, because e.g. on windows it chooses cp1251
def get_file_contents(filename):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            stream = Stream()
            stream.content = file.read()
            stream.size = len(stream.content)
    except(FileNotFoundError):
        print("File \"{0}\" not found!".format(filename))
        exit()

    return stream

# TODO: "x" mode? Or other way to protect against rewriting existing file?
def dump_into_file(filename, output):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(output)

#def accept_symbol(expected, token, input):
#    if (token.symbol == expected):
#        *Token = GetToken(Stream);
#        return True;
#
#    return False;

input = get_file_contents(original_file_name)
tag_count = 0
tagged_output = ""
tags = {}
while (input.at()):
    content_start = input.index
    token = get_token(input)
    if (token.symbol == "\\"):
        token = get_token(input)
        content_end = input.index
        if (token.symbol == "identifier"):
            if (token.content == "begin"):
                token = get_significant_token(input)
                content_end = input.index
                if (token.symbol == "{"):
                    token = get_significant_token(input)
                    content_end = input.index
                    if ((token.symbol == "identifier") and
                        ((token.content == "equation") or
                         (token.content == "subequations") or
                         (token.content == "eqnarray"))):
                        start_token = token
                        while True:
                            if (get_significant_token(input).symbol == "\\"):
                                token = get_significant_token(input)
                                if ((token.symbol == "identifier") and
                                    (token.content == "end")):
                                    if (get_significant_token(input).symbol == "{"):
                                        token = get_significant_token(input)
                                        if ((token.symbol == "identifier") and
                                            ((token.content == start_token.content))):
                                            if (get_significant_token(input).symbol == "}"):
                                                content_end = input.index
                                                tagged_output += "<mt{0}>".format(tag_count)

                                                tag_label = "<mt{0}>".format(tag_count)
                                                tag_content = input.content[content_start:content_end]
                                                tags[tag_label] = tag_content
                                                tag_count += 1

                                                break
                    else:
                        tagged_output += input.content[content_start:content_end]
            elif ((token.content == "cite") or
                  (token.content == "ref")):
                if (get_significant_token(input).symbol == "{"):
                    while (get_significant_token(input).symbol != "}"):
                        continue
                    content_end = input.index
                    tagged_output += "<mt{0}>".format(tag_count)

                    tag_label = "<mt{0}>".format(tag_count)
                    tag_content = input.content[content_start:content_end]
                    tags[tag_label] = tag_content
                    tag_count += 1

            else:
                tagged_output += input.content[content_start:content_end]
        else:
            tagged_output += input.content[content_start:content_end]
    elif ((token.symbol == "$") or
          (token.symbol == "$$")):
        start_token = token
        token = get_significant_token(input)
        while (token.symbol != start_token.symbol):
            token = get_significant_token(input)
        content_end = input.index
        tagged_output += "<mt{0}>".format(tag_count)

        tag_label = "<mt{0}>".format(tag_count)
        tag_content = input.content[content_start:content_end]
        tags[tag_label] = tag_content
        tag_count += 1
    else:
        tagged_output += token.content

# TODO: More differentiation with and without --untag flag? Like do not
# generate tagged_output if untagging or do not generate tags dict if tagging
# etc.
if not untag_requested:
    dump_into_file(tagged_file_name, tagged_output)
else:
    tagged_input = get_file_contents(tagged_file_name)
    untagged_output = ""
    while (tagged_input.at()):
        content_start = tagged_input.index
        token = get_token(tagged_input)
        if (token.symbol == "<"):
            token = get_token(tagged_input)
            content_end = tagged_input.index
            if ((token.symbol == "identifier") and
                (token.content == "mt")):
                token = get_token(tagged_input)
                content_end = tagged_input.index
                if (token.symbol == "number"):
                    tag_count = token.number
                    token = get_token(tagged_input)
                    if (token.symbol == ">"):
                        tag_label = "<mt{0}>".format(tag_count)
                        untagged_output += tags[tag_label]
                    else:
                        untagged_output += tagged_input.content[content_start:content_end]

                else:
                    untagged_output += tagged_input.content[content_start:content_end]
            else:
                untagged_output += tagged_input.content[content_start:content_end]
        else:
            untagged_output += token.content

    dump_into_file(untagged_file_name, untagged_output)

print("Done")
