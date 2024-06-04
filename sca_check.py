#!/usr/bin/env python3
"""
Compliance Automation Script

This script is designed to automate compliance checks and remediation actions
based on a set of predefined rules and solutions. The script leverages a YAML
configuration file to define various compliance checks, each of which can
include file existence checks, directory checks, and command execution checks.

Key Components:
- Utilities for text formatting and command execution.
- Rule parsing and evaluation for compliance checks.
- Automated application of remediation actions based on check results.
- Support for YAML configuration to load checks and solutions.

Usage:
1. Load compliance checks and solutions from a YAML file.
2. Execute all compliance checks and collect results.
3. Optionally apply available remediation actions for failed checks.

Example:
    python sca_check.py /path/to/compliance_rules.yml

Dependencies:
- pyyaml: For loading YAML configuration files.

# todo handle cis variables
"""
import operator
import re
import urllib.request
from os import popen, listdir, system, geteuid
from pathlib import Path
from subprocess import call
from sys import argv

from yaml import load as yaml_load, Loader as YamlLoader

reboot_required = False


# region Utils
class FormatText:
    """
    Text terminal formatter.

    Provides methods to format text for terminal output using ANSI escape codes.

    For more information, see:
    https://en.wikipedia.org/wiki/ANSI_escape_code
    https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences
    """

    tag = "\x1b"  # ANSI escape character
    # region format
    format_bold = "1"
    format_dim = "2"
    format_italic = "3"
    format_underline = "4"
    format_blink = "5"
    format_reverse = "7"
    format_hide = "8"
    format_cross = "9"
    format_box = "52"

    # endregion
    # region color foreground
    color_f_black = "30"
    color_f_red = "31"
    color_f_green = "32"
    color_f_yellow = "33"
    color_f_blue = "34"
    color_f_magenta = "35"
    color_f_cyan = "36"
    color_f_white = "37"
    color_f_black_bright = "90"
    color_f_red_bright = "91"
    color_f_green_bright = "92"
    color_f_yellow_bright = "93"
    color_f_blue_bright = "94"
    color_f_magenta_bright = "95"
    color_f_cyan_bright = "96"
    color_f_white_bright = "97"

    @classmethod
    def color_f_rgb(cls, r, g, b):
        """
        Generates an ANSI escape code for setting the foreground color to an RGB value.

        @param r: Red component (0-255).
        @type r: int
        @param g: Green component (0-255).
        @type g: int
        @param b: Blue component (0-255).
        @type b: int
        @return: ANSI escape code for RGB foreground color.
        @rtype: str
        """
        return f"38;2;{r};{g};{b}"

    # endregion
    # region color background
    color_b_black = "40"
    color_b_red = "41"
    color_b_green = "42"
    color_b_yellow = "43"
    color_b_blue = "44"
    color_b_magenta = "45"
    color_b_cyan = "46"
    color_b_white = "47"
    color_b_black_bright = "100"
    color_b_red_bright = "101"
    color_b_green_bright = "102"
    color_b_yellow_bright = "103"
    color_b_blue_bright = "104"
    color_b_magenta_bright = "105"
    color_b_cyan_bright = "106"
    color_b_white_bright = "107"

    @classmethod
    def color_b_rgb(cls, r, g, b):
        """
        Generates an ANSI escape code for setting the background color to an RGB value.

        @param r: Red component (0-255).
        @type r: int
        @param g: Green component (0-255).
        @type g: int
        @param b: Blue component (0-255).
        @type b: int
        @return: ANSI escape code for RGB background color.
        @rtype: str
        """
        return f"48;2;{r};{g};{b}"

    # endregion
    # region interact
    interact_clear_screen = "2J"
    interact_clear_screen_and_buffer = "3J"
    interact_clear_screen_from_cursor = "1J"
    interact_clear_line = "2K"
    interact_clear_line_from_cursor = "K"
    interact_save_cursor_pos = "s"
    interact_restore_cursor_pos = "u"
    interact_show_cursor = "?25h"
    interact_hide_cursor = "?25l"

    @classmethod
    def interact_cursor_up(cls, cells=1):
        """
        Moves the cursor up by the specified number of cells.

        Abbr: CUU

        @param cells: Number of cells to move up. Defaults to 1.
        @type cells: int
        @return: ANSI escape code for moving cursor up.
        @rtype: str
        """
        return f"{cells}A"

    @classmethod
    def interact_cursor_down(cls, cells=1):
        """
        Moves the cursor down by the specified number of cells.

        Abbr: CUD

        @param cells: Number of cells to move down. Defaults to 1.
        @type cells: int
        @return: ANSI escape code for moving cursor down.
        @rtype: str
        """
        return f"{cells}B"

    @classmethod
    def interact_cursor_forward(cls, cells=1):
        """
        Moves the cursor forward by the specified number of cells.

        Abbr: CUF

        @param cells: Number of cells to move forward. Defaults to 1.
        @type cells: int
        @return: ANSI escape code for moving cursor forward.
        @rtype: str
        """
        return f"{cells}C"

    @classmethod
    def interact_cursor_back(cls, cells=1):
        """
        Moves the cursor back by the specified number of cells.

        Abbr: CUB

        @param cells: Number of cells to move back. Defaults to 1.
        @type cells: int
        @return: ANSI escape code for moving cursor back.
        @rtype: str
        """
        return f"{cells}D"

    @classmethod
    def interact_cursor_next_line(cls, lines=1):
        """
        Moves the cursor to the beginning of the specified number of next lines.

        Abbr: CNL

        @param lines: Number of lines to move down. Defaults to 1.
        @type lines: int
        @return: ANSI escape code for moving cursor to the next line.
        @rtype: str
        """
        return f"{lines}E"

    @classmethod
    def interact_cursor_prev_line(cls, lines=1):
        """
        Moves the cursor to the beginning of the specified number of previous lines.

        Abbr: CPL

        @param lines: Number of lines to move up. Defaults to 1.
        @type lines: int
        @return: ANSI escape code for moving cursor to the previous line.
        @rtype: str
        """
        return f"{lines}F"

    @classmethod
    def interact_cursor_at(cls, line, column):
        """
        Moves the cursor to the specified position.

        Abbr: CUP

        @param line: Line number.
        @type line: int
        @param column: Column number.
        @type column: int
        @return: ANSI escape code for setting cursor position.
        @rtype: str
        """
        return f"{line};{column}H"

    @classmethod
    def interact_scroll_up(cls, lines=1):
        """
        Scrolls the display up by the specified number of lines.

        Abbr: SU

        @param lines: Number of lines to scroll up. Defaults to 1.
        @type lines: int
        @return: ANSI escape code for scrolling up.
        @rtype: str
        """
        return f"{lines}S"

    @classmethod
    def interact_scroll_down(cls, lines=1):
        """
        Scrolls the display down by the specified number of lines.

        Abbr: SD

        @param lines: Number of lines to scroll down. Defaults to 1.
        @type lines: int
        @return: ANSI escape code for scrolling down.
        @rtype: str
        """
        return f"{lines}T"

    # endregion

    # region templates
    @classmethod
    def success(cls, text):
        """
        Formats text with a success style (green color).

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.color_f_green)

    @classmethod
    def error(cls, text):
        """
        Formats text with an error style (red color).

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.color_f_red)

    @classmethod
    def warn(cls, text):
        """
        Formats text with a warning style (yellow color).

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.color_f_yellow)

    @classmethod
    def note(cls, text):
        """
        Formats text with a note style (cyan color and bold).

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.color_f_cyan, cls.format_bold)

    @classmethod
    def bold(cls, text):
        """
        Formats text with a bold style.

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.format_bold)

    @classmethod
    def underline(cls, text):
        """
        Formats text with an underline style.

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.format_underline)

    @classmethod
    def blink(cls, text):
        """
        Formats text with a blink style.

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.format_blink)

    @classmethod
    def cross(cls, text):
        """
        Formats text with a strikethrough style.

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.format_cross)

    @classmethod
    def box(cls, text):
        """
        Formats text with a box style.

        @param text: Text to format.
        @type text: str
        @return: Formatted text.
        @rtype: str
        """
        return cls.style(text, cls.format_box)

    @classmethod
    def clear_last_n_lines(cls, n: int, text=None):
        """
        Clears the last n lines (and current line) on the terminal.

        @param n: Number of lines to clear.
        @type n: int
        @param text: Optional text to display after clearing.
        @type text: str
        @return: ANSI escape code for clearing lines and optional text.
        @rtype: str
        """
        interactions = cls.clear_current_line()
        for i in range(1, n + 1):
            interactions += cls.interact(
                cls.interact_cursor_prev_line(i),
                cls.interact_clear_line,
            )
        return interactions + (text or "")

    @classmethod
    def clear_current_line(cls, text=None):
        """
        Clears the current line on the terminal.

        @param text: Optional text to display after clearing.
        @type text: str
        @return: ANSI escape code for clearing the current line and optional text.
        @rtype: str
        """
        # move the cursor to the beginning of the line and clear the line
        return cls.interact(
            cls.interact_cursor_prev_line(),
            cls.interact_cursor_next_line(),
            cls.interact_clear_line,
        ) + (text or "")

    @classmethod
    def clear_last_n_cells(cls, n, text=None):
        """
        Clears the last n cells on the terminal line.

        @param n: Number of cells to clear.
        @type n: int
        @param text: Optional text to display after clearing.
        @type text: str
        @return: ANSI escape code for clearing cells and optional text.
        @rtype: str
        """
        return cls.interact(
            cls.interact_cursor_back(n),
            cls.interact_clear_line_from_cursor,
        ) + (text or "")

    @classmethod
    def clear_screen(cls, text=None):
        """
        Clears the terminal screen and buffer.

        @param text: Optional text to display after clearing.
        @type text: str
        @return: ANSI escape code for clearing the screen and optional text.
        @rtype: str
        """
        return cls.interact(cls.interact_clear_screen_and_buffer) + (text or "")

    # endregion

    @classmethod
    def style(cls, text, *styles):
        """
        Applies the specified styles to the text.

        @param text: Text to style.
        @type text: str
        @param styles: List of style codes to apply.
        @return: Styled text.
        @rtype: str
        """
        if not styles:
            return text

        return f"{cls.tag}[{';'.join(styles)}m{text}{cls.tag}[0m"

    @classmethod
    def interact(cls, *interactions):
        """
        Generates ANSI escape codes for the specified interactions.

        @param interactions: List of interaction codes.
        @return: ANSI escape codes.
        @rtype: str
        """
        if not interactions:
            return ""

        return f"{cls.tag}[" + f"{cls.tag}[".join(interactions)


def wrap_text(text, characters_per_line=130):
    """
    Wraps the provided text to a specified number of characters per line.

    This function takes a multi-line string and wraps each line to ensure
    that no line exceeds the specified number of characters. It preserves
    the indentation of each line.

    Example
    =======
        >>> t = "This is a very long line that needs to be wrapped because it exceeds the maximum allowed characters per line."
        >>> wrap_text(t, characters_per_line=20)
        'This is a very long\\nline that needs to be\\nwrapped because it exceeds\\nthe maximum allowed\\ncharacters per line.'

    @param text: The input text to be wrapped.
    @type text: str
    @param characters_per_line: The maximum number of characters per line. Defaults to 130.
    @type characters_per_line: int
    @return: The text with each line wrapped to the specified length.
    @rtype: str
    """

    def wrap_line(line, _add_lf=False):
        """
        Wraps a single line to the specified number of characters.

        @param line: The input line to be wrapped.
        @type line: str
        @param _add_lf: Used Internally to determine whether to add \n separator before wrapping. Defaults to False.
        @type _add_lf: bool
        @return: The wrapped line.
        @rtype: str
        """
        wrapped_line = ""
        if _add_lf:
            for character in line:
                if character.isspace():
                    break
                else:
                    wrapped_line += character
            else:
                # If the line ended and no spaces were found, return the line as is
                return line

            # Remove the processed part of the line (including the space)
            line = line[len(wrapped_line) + 1:]
            wrapped_line += "\n"

        for i, character in enumerate(line):
            if i >= characters_per_line - 1:
                # Recursively wrap the remaining part of the line
                wrapped_line += wrap_line(line[i:], _add_lf=True)
                break
            else:
                wrapped_line += character
        return wrapped_line

    output = []
    for text_line in text.split("\n"):
        prepend = ""
        for ch in text_line:
            if ch.isspace():
                prepend += ch
            else:
                break

        # Preserve the indentation and wrap the line
        output.append(
            prepend + f"\n{prepend}".join(wrap_line(text_line.strip()).split("\n"))
        )
    return "\n".join(output)


def execute(cmd, ask=False, timeout=0):
    """
    Executes a shell command and optionally asks for confirmation.

    Example
    =======
        >>> execute("echo hello")
        'hello\\n'
        >>> execute("sleep 2", timeout=1)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        TimeoutError: Command: sleep 2

    @param cmd: The command to execute.
    @type cmd: str
    @param ask: If True, asks for confirmation before executing the command.
    @type ask: bool
    @param timeout: The maximum time (in seconds) to allow the command to run. If 0, no timeout is set.
    @type timeout: int
    @return: The output of the command.
    @rtype: str
    @raise TimeoutError: If the command times out.
    """
    # Ask for confirmation before executing the command, if required
    if ask and not confirm(None, FormatText.note(f"{cmd}\nExecute?")):
        return ""

    # Prepare the command with a timeout, if specified
    if timeout:
        _cmd = f'timeout {timeout} {cmd} 2>&1; [ $? -eq 124 ] && echo "BASH_TIMEOUT";'
    else:
        _cmd = f"{cmd} 2>&1"

    # Execute the command and capture its output
    with popen(_cmd) as f:
        output = f.read()

    # Check if the command output indicates a timeout
    if output.endswith("BASH_TIMEOUT\n"):
        raise TimeoutError(f"Command: {cmd}")

    # Print the command output if confirmation was requested
    if ask:
        print(FormatText.note(output))

    return output


def indent(text, level, spaces=False):
    """
    Change the indentation level of the given text.

    Example
    =======
        >>> indent('hello\\nhi', 1)
        '    hello\\n    hi'
        >>> indent('\\thello\\n\\thi', -2)
        'hello\\nhi'

    @param text: The text to be indented.
    @type text: str
    @param level: The number of levels to adjust the indentation by. Positive values increase indentation, negative values decrease it.
    @type level: int
    @param spaces: If True, use 4 spaces for indentation; otherwise, use tabs.
    @type spaces: bool
    @return: The text with adjusted indentation.
    @rtype: str
    """
    # Prepare the output list to accumulate the processed lines
    output = []

    # Determine the indentation character based on the 'spaces' parameter
    ch = " " * 4 if spaces else "\t"

    # Process each match from the regular expression to match lines with indentation
    for match in re.finditer(r"^((?: {4}|\t)+)?(.*)$", text, flags=re.M):
        group_indention, group_text = match.groups()

        # Calculate the current indentation level
        if group_indention is None:
            curr_level = 0
        else:
            curr_level = group_indention.count("    ") + group_indention.count("\t")

        # Calculate the new indentation level
        new_level = curr_level + level

        # Append the appropriately indented line to the output list
        if new_level <= 0:
            output.append(group_text)
        else:
            output.append(ch * new_level + group_text)

    # Join the output list into a single string with newline characters
    return "\n".join(output)


# endregion


# region Check
class Check:
    """
    A class to represent a check with its associated rules, solutions, and status.

    @cvar checks: A class attribute to keep track of all check instances.
    @type checks: list[Check]
    @cvar passed: A class attribute to keep track of passed check instances.
    @type passed: list[Check]
    @cvar failed: A class attribute to keep track of failed check instances.
    @type failed: list[Check]
    @cvar not_applicable: A class attribute to keep track of not applicable check instances.
    @type not_applicable: list[Check]
    @ivar id: The identifier for the check.
    @type id: int
    @ivar title: The title of the check.
    @type title: str
    @ivar description: The description of the check.
    @type description: str
    @ivar rationale: The rationale behind the check.
    @type rationale: str
    @ivar remediation: The remediation steps for the check.
    @type remediation: str
    @ivar compliance: The compliance information for the check.
    @type compliance: list[dict[str, list[str]]]
    @ivar references: The list of external references.
    @type references: list[str]
    @ivar condition: The condition to be met for the check.
    @type condition: str
    @ivar rules: The rules associated with the check.
    @type rules: Rules
    @ivar regex_type: The regex type to check against.
    @type regex_type: str
    @ivar solution: The solution associated with the check.
    @type solution: Solution
    @ivar status: The status of the check ("PASSED", "FAILED", "NOT_APPLICABLE").
    @type status: str | None
    """

    checks = []
    passed = []
    failed = []
    not_applicable = []

    def __init__(self, check):
        """
        Initializes the Check object with the given check dictionary.

        Check Model::
            {
                "id": 1,
                "title": "Title",
                "description": "Description",
                "rationale": "Rationale",
                "remediation": "Remediation",
                "compliance": [{"key": ["value"]}],
                "references": ["reference"],
                "condition": "any or all or none",
                "rules": ["Rule Regex"],
                "regex_type": "RegexType",
                "solution": SolutionModel,
            }

        @param check: The dictionary containing check information.
        @type check: dict
        """
        self.id = check["id"]
        self.title = check["title"]
        self.description = check.get("description", "")
        self.rationale = check.get("rationale", "")
        self.remediation = check.get("remediation", "")
        self.compliance = check.get("compliance", [])
        self.references = check.get("references", [])
        self.condition = check["condition"]
        self.rules = Rules(self.id, self.condition, check["rules"])
        self.regex_type = check.get("regex_type")  # todo
        self.solution = Solution(self.id, check["solution"])
        self.status = None

    def __str__(self):
        """
        Returns a string representation of the check.

        @return: A string representation of the check.
        @rtype: str
        """
        # Format the check details into a string
        txt = f"ID: {self.id}\n"
        if self.title:
            txt += f"Title:\n\t{self.title.strip()}\n"
        if self.rationale:
            txt += wrap_text(f"Rationale:\n\t{self.rationale.strip()}\n")
        if self.remediation:
            txt += wrap_text(f"Remediation:\n\t{self.remediation.strip()}\n")
        if self.description:
            txt += wrap_text(f"Description:\n\t{self.description.strip()}\n")
        if self.regex_type:
            txt += f"RegexType:\n\t{self.regex_type.strip()}\n"

        # Add references information
        if self.references:
            txt += "References:\n\t- " + "\n\t- ".join(self.references) + "\n"

        # Add rules information
        txt += str(self.rules)

        # Add compliance information
        if self.compliance:
            txt += "\nCompliance\n\t- " + "\n\t- ".join(
                [
                    f"{k}: {','.join(v)}"
                    for item in self.compliance
                    for k, v in item.items()
                ]
            )

        # Add solution information
        txt += "\n" + str(self.solution)

        return txt

    def __repr__(self):
        """
        Returns a string representation of the check.

        @return: A string representation of the check.
        @rtype: str
        """
        return self.__str__()

    @classmethod
    def check_all(cls):
        """
        Class method to check all instances of Check.

        Asks for confirmation before starting the checks.
        Prints a summary report of passed, failed, and not applicable checks.
        Offers to apply solutions for failed checks if available.
        """
        if not confirm("Checking", "Start Checks?"):
            return

        # Execute check for each instance of Check
        for check in cls.checks:
            check.check()

        # Print summary report
        print("\n\nCheck Report")
        print(FormatText.success("[    PASSED    ]"), len(cls.passed))
        print(FormatText.error("[    FAILED    ]"), len(cls.failed))
        print(
            FormatText.style("[NOT APPLICABLE]", FormatText.color_f_black_bright),
            len(cls.not_applicable),
        )
        print()

        # Offer to apply solutions for failed checks
        available_solutions = [ins for ins in cls.failed if ins.solution.available]
        print(FormatText.success("[   SOLUTIONS  ]"), len(available_solutions))

        if available_solutions and confirm("Solutions", "Apply Available Solutions?"):
            for solution in available_solutions:
                solution.apply_solution()

    @classmethod
    def class_repr(cls):
        """Class method to print the representation of all checks."""
        for check in cls.checks:
            print(check)

    @classmethod
    def _load(cls, path):
        """
        Class method to load or download yml configurations.

        @param path: The path or url to the file containing configuration information.
        @type path: str
        """
        if path.startswith('http'):
            # download
            print(FormatText.success(f"Downloading configurations from {path}"))
            return yaml_load(urllib.request.urlopen(path), YamlLoader)
        else:
            # load
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(p)
            if p.is_dir():
                raise IsADirectoryError(p)

            with open(p, "r") as f:
                return yaml_load(f, YamlLoader)

    @classmethod
    def load(cls, cis, solutions=None, white_listed_ids=None):
        """
        Class method to load checks from a file.

        B{Note} If `solutions` is not given this function will try to load solutions from {cis}_solutions.yml

        @param cis: The path or url to the file containing check information.
        @type cis: str
        @param solutions: The path or url to the file containing solutions information.
        @type solutions: str | None
        @param white_listed_ids: If specified only these checks will be loaded
        @type white_listed_ids: list[int] | None
        """
        print("Loading rules ...")

        # load cis
        content = cls._load(cis)

        # load solutions
        try:
            if solutions is None:
                last_dot_index = cis.rfind(".")
                solutions = cls._load(cis[:last_dot_index] + "_solutions" + cis[last_dot_index:])
            else:
                solutions = cls._load(solutions)
        except:
            print(FormatText.style("Error loading solutions", FormatText.color_f_red, FormatText.format_blink))
            solutions = []

        print(FormatText.note(f"{'=' * 32} {content['policy']['id']} {'=' * 32}"))
        print(FormatText.note(content["policy"]["name"]))
        print(FormatText.note(wrap_text(content["policy"]["description"])))

        # check sca requirements
        if not Rules(
                0, content["requirements"]["condition"], content["requirements"]["rules"]
        ).check():
            print(FormatText.error("Requirements not satisfied"))
            exit()

        for check in content["checks"]:
            if white_listed_ids and check["id"] not in white_listed_ids:
                continue

            solution = check.get("solution")
            if solution is None:
                # No solution found within the main configuration. try to find solution from the loaded file
                for item in solutions:
                    if item["id"] == check["id"]:
                        solution = item["solution"]
            check["solution"] = solution

            # Add the instance to the class-level checks list
            cls.checks.append(cls(check))

        print(FormatText.success("Loaded all rules"))

    def check(self):
        """
        Executes the check and updates the status.

        @return: True if the check passes, False otherwise.
        @rtype: bool
        """
        res = self.rules.check()
        if res:
            self.status = "PASSED"
            self.__class__.passed.append(self)
            print(FormatText.success(f"[    PASSED    ]"), self.id, self.title)
        elif res is False:
            self.status = "FAILED"
            self.__class__.failed.append(self)
            print(FormatText.error(f"[    FAILED    ]"), self.id, self.title)
        elif res is None:
            self.status = "NOT_APPLICABLE"
            self.__class__.not_applicable.append(self)
            print(
                FormatText.style(f"[NOT APPLICABLE]", FormatText.color_f_black_bright),
                self.id,
                self.title,
            )

        return res

    def apply_solution(self):
        """
        Applies the solution associated with the check.

        Attempts to apply the solution up to four times if necessary.
        Asks for confirmation before each attempt and prints the progress.
        """
        print("\n")
        if not confirm(self.title, f"{self}\nApply?"):
            return

        for retry in range(self.solution.recheck and 5 or 1):
            if retry == 4:
                print(
                    FormatText.error(
                        "Reached Maximum tries to apply the solution. Moving on..."
                    )
                )
                return
            if retry > 0:
                print("Rechecking ...")
                if self.check():
                    return
                print(FormatText.error(f"Recheck failed. Retrying {retry}/3"))
                if not confirm(None, "Retry?"):
                    return

            print(f"\n{'-' * 12} APPLY START {'-' * 12}")
            self.solution.apply()
            print(f"{'-' * 12} APPLY END   {'-' * 12}\n")


class Rules:
    """
    A class to represent a collection of rules with a specific condition

    @ivar condition: The condition to be met ("all", "any", "none").
    @type condition: str
    @ivar parsed: The list of parsed rules.
    @type parsed: list[Rule]
    """

    def __init__(self, check_id, condition, rules):
        """
        Initializes the Rules object with the given check_id, condition, and rules.

        @param check_id: The identifier for the check.
        @type check_id: int
        @param condition: The condition to be met ("all", "any", "none").
        @type condition: str
        @param rules: The list of rule strings to be parsed and executed.
        @type rules: list[str]
        """
        self.condition = condition

        # First, do existence checks
        existence_check_rules = []
        non_existence_check_rules = []

        for rule in rules:
            parsed_rule = Rule(check_id, rule)
            if parsed_rule.parsed is not None and parsed_rule.parsed.tag in (
                    "FileExistence",
                    "DirExistence",
                    "DirContains",
            ):
                # Add existence check rules to the corresponding list
                existence_check_rules.append(parsed_rule)
            else:
                # Add non-existence check rules to the corresponding list
                non_existence_check_rules.append(parsed_rule)

        self.parsed = existence_check_rules + non_existence_check_rules

    def __str__(self):
        """
        Returns a string representation of the rules.

        @return: A string representation of the rules.
        @rtype: str
        """
        return f"Checks (Condition: {self.condition}):\n\t- " + "\n\t- ".join(
            [str(rule) for rule in self.parsed]
        )

    def __repr__(self):
        """
        Returns a string representation of the rules.

        @return: A string representation of the rules.
        @rtype: str
        """
        return self.__str__()

    def check(self):
        """
        Executes the parsed rules based on the condition and returns the result.

        @return: True if the condition is met, False if not and None if NotApplicable.
        @rtype: bool | None
        @raise ValueError: If the condition is invalid.
        """
        if self.condition == "all":
            # Check if all rules pass
            not_applicable = False
            for rule in self.parsed:
                res = rule.check()
                if res is False:
                    return False
                if res is None:
                    not_applicable = True
            if not_applicable:
                return None
            return True
        elif self.condition == "any":
            # Check if any rule passes
            not_applicable = False
            for rule in self.parsed:
                res = rule.check()
                if res:
                    return True
                elif res is None:
                    not_applicable = True
            if not_applicable:
                return None
            return False
        elif self.condition == "none":
            # Check if no rule passes
            not_applicable = False
            for rule in self.parsed:
                res = rule.check()
                if res:
                    return False
                elif res is None:
                    not_applicable = True
            if not_applicable:
                return None
            return True
        else:
            raise ValueError(f"Bad Condition {self.condition}")


class Rule:
    """
    A class to represent and execute a rule based on given conditions and checks.

    @ivar check_id: The identifier for the check.
    @type check_id: int
    @ivar rule: The rule string to be parsed and executed.
    @type rule: str
    @ivar parsed: The parsed rule object.
    @type parsed: ParsedRule | None
    """

    def __init__(self, check_id, rule):
        """
        Initializes the Rule object with the given check_id and rule.

        @param check_id: The identifier for the check.
        @type check_id: int
        @param rule: The rule string to be parsed and executed.
        @type rule: str
        """
        self.check_id = check_id
        self.rule = rule
        try:
            self.parsed = self.parse()
        except Exception as e:
            # Print a warning if there is an error parsing the rule
            print(
                FormatText.warn("[RuleParseError]"),
                check_id,
                rule,
                FormatText.underline(f"{e.__class__.__name__}({e.args})"),
            )
            self.parsed = None

    def __str__(self):
        """
        Returns a string representation of the rule.

        @return: A string representation of the rule.
        @rtype: str
        """
        return self.rule

    def __repr__(self):
        """
        Returns a string representation of the rule.

        @return: A string representation of the rule.
        @rtype: str
        """
        return self.__str__()

    def parse(self):
        """
        Parses the rule string into a ParsedRule object.

        @return: The parsed rule object.
        @rtype: ParsedRule
        @raise ValueError: If the rule string is invalid.
        """
        rule = self.rule.split("->")

        # Strip whitespace from each part of the rule
        for i, item in enumerate(rule):
            rule[i] = item.strip()

        to_check = rule[0]
        if to_check.startswith("not "):
            revert = True
            to_check = to_check[4:]
        else:
            revert = False

        if to_check.startswith("f:"):
            if len(rule) == 1:
                return ParsedRule(
                    "FileExistence",
                    self.check_file_exists,
                    revert,
                    path=Path(to_check[2:]),
                )
            elif len(rule) == 2:
                return ParsedRule(
                    "RegexAgainstFile",
                    self.check_regex_against_file,
                    revert,
                    path=Path(to_check[2:]),
                    regex=Regex(rule[1]),
                )
            else:
                raise ValueError("Invalid file check rule")
        elif to_check.startswith("c:"):
            if len(rule) == 2:
                return ParsedRule(
                    "RegexAgainstCommand",
                    self.check_regex_against_command,
                    revert,
                    cmd=to_check[2:],
                    regex=Regex(rule[1]),
                )
            else:
                raise ValueError(f"Invalid command check rule")
        elif to_check.startswith("d:"):
            if len(rule) == 1:
                return ParsedRule(
                    "DirExistence",
                    self.check_dir_exists,
                    revert,
                    path=Path(to_check[2:]),
                )
            if len(rule) == 2:
                return ParsedRule(
                    "DirContains",
                    self.check_dir_contains,
                    revert,
                    path=Path(to_check[2:]),
                    file_pattern=Regex(rule[1]),
                )
            elif len(rule) == 3:
                return ParsedRule(
                    "RegexAgainstDir",
                    self.check_regex_against_dir,
                    revert,
                    path=Path(to_check[2:]),
                    file_pattern=Regex(rule[1]),
                    regex=Regex(rule[2]),
                )
            else:
                raise ValueError("Invalid glob check rule")
        elif to_check.startswith("p:"):
            if len(rule) == 1:
                return ParsedRule(
                    "CheckProcessExists",
                    self.check_process_exists,
                    revert,
                    process_name=to_check[2:],
                )
            else:
                raise ValueError("Invalid process check rule")
        elif to_check.startswith("r:"):
            # todo
            raise ValueError("r: is not implemented")
        else:
            raise ValueError(f"Invalid rule")

    def check(self):
        """
        Executes the parsed rule and returns the result.

        @return: True if the rule check passes, False if not and None if NotApplicable.
        @rtype: bool | None
        """
        if self.parsed is None:
            return True

        try:
            res = self.parsed.function(**self.parsed.kwargs)
            if self.parsed.revert:
                # Invert the result if the rule is to be reverted
                return not res
            return res
        except Exception as e:
            # Print a warning if there is an error executing the rule
            print(
                FormatText.warn("[RuleCheckError]"),
                self.check_id,
                FormatText.bold(self.parsed.tag),
                self.rule,
                FormatText.underline(f"{e.__class__.__name__}({e.args})"),
            )

    @staticmethod
    def check_regex_against_command(cmd, regex):
        """
        Checks if the regex matches the output of the command.

        @param cmd: The command to be executed.
        @type cmd: str
        @param regex: The regex pattern to check against the command output.
        @type regex: Regex
        @return: True if the regex matches the command output, False otherwise.
        @rtype: bool
        """
        return regex.check(execute(cmd, timeout=10))

    @staticmethod
    def check_process_exists(process_name):
        """
        Checks if the process is running on system.

        @param process_name: The name of the process to be checked.
        @type process_name: str
        @return: True if the process is running, False otherwise.
        @rtype: bool
        """
        return execute(f'pgrep -x "{process_name}" > /dev/null && echo "running"') == "running\n"

    @staticmethod
    def check_file_exists(path):
        """
        Checks if the file exists at the given path.

        @param path: The path to the file.
        @type path: Path
        @return: True if the file exists, False otherwise.
        @rtype: bool
        @raise IsADirectoryError: If the path is a directory.
        """
        if path.exists():
            if path.is_dir():
                raise IsADirectoryError(path)
            return True
        return False

    @staticmethod
    def check_regex_against_file(path, regex):
        """
        Checks if the regex matches the contents of the file.

        @param path: The path to the file.
        @type path: Path
        @param regex: The regex pattern to check against the file contents.
        @type regex: Regex
        @return: True if the regex matches the file contents, False otherwise.
        @rtype: bool
        @raise FileNotFoundError: If the file does not exist.
        @raise IsADirectoryError: If the path is a directory.
        """
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            raise IsADirectoryError(path)

        with open(path, "r") as f:
            return regex.check(f.read())

    @staticmethod
    def check_dir_exists(path):
        """
        Checks if the directory exists at the given path.

        @param path: The path to the directory.
        @type path: Path
        @return: True if the directory exists, False otherwise.
        @rtype: bool
        @raise NotADirectoryError: If the path is not a directory.
        """
        if path.exists():
            if not path.is_dir():
                raise NotADirectoryError(path)
            return True
        return False

    @staticmethod
    def check_dir_contains(path, file_pattern):
        """
        Checks if the directory contains a file matching the given pattern.

        @param path: The path to the directory.
        @type path: Path
        @param file_pattern: The regex pattern to match the file names.
        @type file_pattern: Regex
        @return: True if a matching file is found, False otherwise.
        @rtype: bool
        @raise FileNotFoundError: If the directory does not exist.
        @raise NotADirectoryError: If the path is not a directory.
        """
        if not path.exists():
            raise FileNotFoundError(path)
        if not path.is_dir():
            raise NotADirectoryError(path)

        for file_name in listdir(path):
            file = path / file_name
            if file.is_file() and file_pattern.check(file_name):
                return True
        return False

    @staticmethod
    def check_regex_against_dir(path, file_pattern, regex):
        """
        Checks if the regex matches the contents of any file in the directory matching the given pattern.

        @param path: The path to the directory.
        @type path: Path
        @param file_pattern: The regex pattern to match the file names.
        @type file_pattern: Regex
        @param regex: The regex pattern to check against the file contents.
        @type regex: Regex
        @return: True if a matching file content is found, False otherwise.
        @rtype: bool
        @raise FileNotFoundError: If the directory does not exist.
        @raise NotADirectoryError: If the path is not a directory.
        """
        if not path.exists():
            raise FileNotFoundError(path)
        if not path.is_dir():
            raise NotADirectoryError(path)

        for file_name in listdir(path):
            file = path / file_name
            if file.is_file() and file_pattern.check(file_name):
                with open(file, "r") as f:
                    if regex.check(f.read()):
                        return True
        return False


class ParsedRule:
    """
    A class to represent a parsed rule with a specific tag, function, and optional parameters.

    @ivar tag: The tag associated with the rule.
    @type tag: str
    @ivar function: The function to be executed by the rule.
    @type function: typing.Callable
    @ivar revert: Indicates whether the rule should be reverted.
    @type revert: bool
    @ivar kwargs: Additional keyword arguments for the function.
    @type kwargs: dict
    """

    def __init__(self, tag, function, revert, **kwargs):
        """
        Initializes the ParsedRule object with the given parameters.

        @param tag: The tag associated with the rule.
        @type tag: str
        @param function: The function to be executed by the rule.
        @type function: typing.Callable
        @param revert: Indicates whether the rule should be reverted.
        @type revert: bool
        @param kwargs: Additional keyword arguments for the function.
        """
        self.tag = tag
        self.function = function
        self.revert = revert
        self.kwargs = kwargs

    def __str__(self):
        """
        Returns a string representation of the parsed rule.

        @return: A string representation of the parsed rule.
        @rtype: str
        """
        kwargs = ", ".join(
            [f'{k}="{v}"' for k, v in self.kwargs.items()] + [f"revert={self.revert}"]
        )
        return FormatText.underline(f"{self.function.__name__}({kwargs})")

    def __repr__(self):
        """
        Returns a string representation of the parsed rule.

        @return: A string representation of the parsed rule.
        @rtype: str
        """
        return self.__str__()


class Regex:
    """
    A class to represent and manipulate custom wazuh regex patterns for text matching.

    @cvar ops: A dictionary mapping comparison operators as strings to their corresponding functions in the `operator` module.
    @type ops: dict
    @ivar pattern: The original regex pattern string.
    @type pattern: str
    @ivar chains: A list of sub-patterns derived from the original pattern, split by '&&'.
    @type chains: list
    """

    ops = {
        "<": operator.lt,
        "<=": operator.le,
        "=<": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
        "=>": operator.ge,
        ">=": operator.ge,
        ">": operator.gt,
    }

    def __init__(self, pattern):
        """
        Initializes the Regex object with the given pattern.

        @param pattern: The Wazuh regex pattern string.
        @type pattern: str
        """
        self.pattern = pattern
        self.chains = [
            item.strip()
            for item in (
                pattern.replace("*", "*?")
                .replace("\\.", "REGEX_DOT")
                .replace(".", "\\.")
                .replace("REGEX_DOT", ".")
                .replace("\\w", "[A-Za-z0-9-@_]")
                .replace("\\W", "[^A-Za-z0-9-@_]")
                .replace("\\s", "[ ]")
                .replace("\\S", "[^ ]")
                .replace("\\p", """[()*+,-.:;<=>?[]!"'#$%&|{}]""")
            ).split("&&")
        ]

    def __str__(self):
        """
        Returns the original pattern string.

        @return: The original pattern string.
        @rtype: str
        """
        return self.pattern

    def __repr__(self):
        """
        Returns the original pattern string.

        @return: The original pattern string.
        @rtype: str
        """
        return self.__str__()

    def check(self, text):
        """
        Checks if the given text matches the regex pattern according to the specified rules.

        @param text: The text to be checked against the pattern.
        @type text: str
        @return: True if the text matches the pattern, False otherwise.
        @rtype: bool
        """
        for line in text.split("\n"):
            for chain in self.chains:
                if chain.startswith("r:"):
                    # Regex match required
                    if not bool(re.findall(chain[2:], line, flags=re.I)):
                        break
                elif chain.startswith("!r:"):
                    # Regex non-match required
                    if bool(re.findall(chain[3:], line, flags=re.I)):
                        break
                elif chain.startswith("n:"):
                    # Numeric comparison required
                    pattern, op, standard_value = re.findall(
                        r"n:(.*)?\s+compare\s+([<>=!]*)\s+(\d+)", chain, flags=re.I
                    )[0]
                    value = re.findall(pattern, line, flags=re.I)
                    if not value or not self.ops[op](
                            int(value[0]), int(standard_value)
                    ):
                        break
                else:
                    # Direct string comparison
                    if chain != line:
                        break
            else:
                # All chains matched
                return True
        return False


# endregion


# region Solution
class Solution:
    """
    A class to represent a solution for a check.

    @ivar check_id: The identifier for the associated check.
    @type check_id: int
    @ivar recheck: Whether to recheck after applying the solution.
    @type recheck: bool | None
    @ivar acts: The actions to be performed as part of the solution.
    @type acts: SolutionActs | None
    """

    def __init__(self, check_id, solution):
        """
        Initializes the Solution object with the given check id and solution dictionary.

        Solution Model::
            {
                "recheck": bool (default true)
                "acts": [{
                    "function": "name",
                    "args": ["arg1"],
                    "kwargs": {"kwarg1": "val1"},
                    "on_response": [{
                        "value": "value to expect from function call",
                        "acts": []  # like above
                    }]
                }]
            }


        Available Functions and their arguments
        - execute(cmd, ask=True)
        - confirm(title, prompt)
        - def note(title, prompt)
        - choose(title, prompt, *choices)
        - def nano(file, prompt)
        - def set_reboot_required()
        - def backup(path)

        @param check_id: The identifier for the associated check.
        @type check_id: int
        @param solution: The dictionary containing the solution information.
        @type solution: dict
        """
        self.check_id = check_id

        if solution:
            self.recheck = solution.get("recheck", True)

            try:
                self.acts = SolutionActs(check_id, solution["acts"])
            except Exception as e:
                print(
                    FormatText.warn("[SolutionParseError]"),
                    check_id,
                    FormatText.underline(f"{e.__class__.__name__}({e.args})"),
                )
                self.acts = None
        else:
            self.recheck = None
            self.acts = None

    def __str__(self):
        """
        Returns a string representation of the solution.

        @return: A string representation of the solution.
        @rtype: str
        """
        if self.available:
            return f"Solutions (recheck={self.recheck}):\n" + indent(str(self.acts), 1)
        else:
            return "Solutions: NotAvailable"

    def __repr__(self):
        """
        Returns a string representation of the solution.

        @return: A string representation of the solution.
        @rtype: str
        """
        return self.__str__()

    @property
    def available(self):
        """
        Checks if the solution is available.

        @return: True if the solution is available, False otherwise.
        @rtype: bool
        """
        return self.acts is not None

    def apply(self):
        """Executes the actions defined in the solution."""
        if not self.available:
            return

        self.acts.apply()


class SolutionActs:
    """
    A class to represent a collection of actions for a solution.

    @ivar parsed_acts: A list of parsed SolutionAct objects.
    @type parsed_acts: list[SolutionAct]
    """

    def __init__(self, check_id, acts):
        """
        Initializes the SolutionActs object with the given check id and list of actions.

        @param check_id: The identifier for the associated check.
        @type check_id: int
        @param acts: A list of action dictionaries.
        @type acts: list[dict]
        """
        self.parsed_acts = [SolutionAct(check_id, act) for act in acts]

    def __str__(self):
        """
        Returns a string representation of the SolutionActs object.

        @return: A string representation of the SolutionActs object.
        @rtype: str
        """
        return "- " + "\n- ".join(str(item) for item in self.parsed_acts)

    def __repr__(self):
        """
        Returns a string representation of the SolutionActs object.

        @return: A string representation of the SolutionActs object.
        @rtype: str
        """
        return self.__str__()

    def apply(self):
        """Applies all the actions defined in the SolutionActs object."""
        for action in self.parsed_acts:
            action.apply()


class SolutionAct:
    """
    A class to represent an individual action for a solution.

    @ivar function: The name of the function to be called.
    @type function: str
    @ivar args: The arguments to be passed to the function.
    @type args: list
    @ivar kwargs: The keyword arguments to be passed to the function.
    @type kwargs: dict
    @ivar callable_func: The decorated function to be called.
    @type callable_func: typing.Callable
    @ivar on_response: A list of dictionaries containing actions to be performed based on the response value.
    @type on_response: list[dict[str, Any|SolutionActs]]
    """

    def __init__(self, check_id, act):
        """
        Initializes the SolutionAct object with the given check id and action.

        @param check_id: The identifier for the associated check.
        @type check_id: int
        @param act: The action dictionary containing function details.
        @type act: dict
        """
        self.function = act["function"]
        self.args = act.get("args", [])
        self.kwargs = act.get("kwargs", {})

        if self.function == "execute":
            self.kwargs.setdefault("ask", True)

        self.callable_func = self.decorate()
        self.on_response = [
            {
                "value": response["value"],
                "acts": SolutionActs(check_id, response["acts"]),
            }
            for response in act.get("on_response", [])
        ]

    def __str__(self):
        """
        Returns a string representation of the SolutionAct object.

        @return: A string representation of the SolutionAct object.
        @rtype: str
        """
        f_args = ""
        if self.args:
            f_args = ", ".join(f"'{arg}'" for arg in self.args)
        if self.kwargs:
            if f_args:
                f_args += ", "
            f_args += ", ".join(f"{k}={v}" for k, v in self.kwargs.items())

        txt = f"{self.function}({f_args})"
        if self.on_response:
            for response in self.on_response:
                txt += f"\n\t\u21aa On Value {response['value']}: \n" + indent(
                    str(response["acts"]), 2
                )

        return txt

    def __repr__(self):
        """
        Returns a string representation of the SolutionAct object.

        @return: A string representation of the SolutionAct object.
        @rtype: str
        """
        return self.__str__()

    def apply(self):
        """Applies the action defined in the SolutionAct object."""
        resp = self.callable_func()
        for response in self.on_response:
            if resp == response["value"]:
                response["acts"].apply()

    def decorate(self):
        """
        Decorates the function specified in the action.

        @return: The decorated function.
        @rtype: function
        @raise ValueError: If the function is not callable
        @raise KeyError: If the function is not found
        """
        function = globals()[self.function]

        if not callable(function):
            raise ValueError(f"{self.function} not callable")

        def caller():
            return function(*self.args, **self.kwargs)

        return caller


def confirm(title, prompt):
    """
    Show the prompt and get confirmation from the user.

    @param title: The title to display before the prompt.
    @type title: str | None
    @param prompt: The message to display as the prompt.
    @type prompt: str
    @return: True if the user confirms, False otherwise.
    @rtype: bool
    @raise KeyboardInterrupt: If a keyboard interrupt (Ctrl+C) is detected.
    """
    if title is not None:
        print(FormatText.success(f"{'=' * 32} {title} {'=' * 32}"))
    print(prompt)

    # Get confirmation and handle keyboard interrupts
    input_res = "n"
    try:
        input_res = input(FormatText.blink("Proceed? [Y/n] (default=yes): "))
        interrupted = None
    except KeyboardInterrupt as e:
        interrupted = e
    finally:
        res = input_res == "" or input_res in ("yes", "y", "Y")

    # Prepare text to be printed before displaying the result
    if interrupted is None:
        # If there was no interruption, a newline is inserted due to input
        pre_print = FormatText.clear_last_n_lines(1)
    else:
        # If there was a keyboard interrupt, no new lines were inserted
        pre_print = FormatText.clear_current_line()

    # Move the cursor to the appropriate position before displaying the result
    pre_print += FormatText.interact(
        FormatText.interact_cursor_prev_line(1),
        FormatText.interact_cursor_forward(len(prompt.split("\n")[-1]) + 10),
    )

    # Display the result (accepted or declined)
    if res:
        print(pre_print + FormatText.success("[ACCEPTED]"))
    else:
        print(pre_print + FormatText.error("[DECLINED]"))

    # Raise the interrupted exception if it occurred
    if interrupted is not None:
        raise interrupted

    return res


def note(title, prompt):
    """
    Display a note with an optional title.

    @param title: The title of the note.
    @type title: str | None
    @param prompt: The content of the note.
    @type prompt: str
    """
    if title is not None:
        print(f"{'-' * 12} {title} {'-' * 12}")
    print(FormatText.note(prompt))


def choose(title, prompt, *choices):
    """
    Display a prompt with multiple choices and return the index of the chosen item.

    @param title: The title of the prompt. If None, a default title "Choose" is used.
    @type title: str | None
    @param prompt: The content of the prompt.
    @type prompt: str
    @param choices: The list of choices to display.
    @type choices: Any
    @return: The index of the chosen item. If aborted, returns None.
    @rtype: int | None
    """
    if title is None:
        title = "Choose"
    print(f"{'-' * 12} {title} {'-' * 12}")
    print(prompt)

    # Print the choices with their corresponding index
    print("\n".join(f"{i}) {choice}" for i, choice in enumerate(choices)))
    print()

    interrupted = None
    chosen_id = None
    chosen_item = None
    try:
        chosen_id = int(
            input(
                FormatText.blink("What do you choose? (press any other key to abort): ")
            )
        )
        chosen_item = choices[chosen_id]
    except KeyboardInterrupt as e:
        interrupted = e
    except:
        pass

    # Prepare text to be printed before displaying the result
    if interrupted is None:
        # If there was no interruption, a newline is inserted due to input
        pre_print = FormatText.clear_last_n_lines(1)
    else:
        # If there was a keyboard interrupt, no new lines were inserted
        pre_print = FormatText.clear_current_line()

    # Display the result
    if chosen_id is None:
        print(pre_print + FormatText.error(f"{'-' * 12} ABORTED {'-' * 12}"))
    else:
        print(pre_print + FormatText.success(f"Selected: {chosen_item}"))

    # Raise the interrupted exception if it occurred
    if interrupted is not None:
        raise interrupted

    return chosen_id


def nano(file, prompt):
    """
    Launches the Nano text editor to edit a file if confirmed by the user.

    @param file: The path to the file to be edited.
    @type file: str
    @param prompt: The comment or message displayed to the user when confirming the action.
    @type prompt: str
    """
    if confirm("Launching Text Editor", prompt):
        call(["nano", file])


def set_reboot_required():
    """Sets a global flag indicating that a system reboot is required."""
    global reboot_required
    reboot_required = True


def backup(path):
    """
    Create a backup of a file or directory.

    @param path: The path to the file or directory to be backed up.
    @type path: str
    """
    path = Path(path)
    if not path.exists():
        # If the path does not exist, return without performing backup
        return

    # Display a note about backing up the file/directory
    note(None, f"Backing up {path}")

    parent = path.parent
    name = path.name
    backup_path = parent / (name + ".backup")
    for i in range(1000):
        if backup_path.exists():
            print(FormatText.warn(f"Backup {path} already exists"))
        else:
            execute(f"cp -r {path} {backup_path}", ask=True)
            return

        # If the backup path already exists, generate a new one with an incremental suffix
        backup_path = parent / (name + f".backup.{i}")

    # If all backup paths are taken, overwrite the main backup
    print(
        FormatText.warn("All Backup Paths already exist (overwriting on main backup)")
    )
    execute(f"cp -r {path} {parent / (name + '.backup')}", ask=True)


# endregion


if __name__ == "__main__":
    if geteuid() != 0:
        exit(
            "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'"
        )

    system("clear")

    try:
        cis_path = argv[1]
    except IndexError:
        raise ValueError("Must specify url or path ro cus_rules.yml")

    try:
        solutions_path = argv[2]
        if not solutions_path:
            raise IndexError
        print(FormatText.note(f"Solutions path: {solutions_path}"))
    except IndexError:
        print(FormatText.note("Solutions path not specified. Will be detected automatically"))
        solutions_path = None

    try:
        whitelisted_checks = [int(i) for i in argv[3].split(",")]
        print(FormatText.note(f"Only Checking IDs: {whitelisted_checks}"))
    except:
        print(FormatText.note("No whitelisted checks specified. Will check all available Checks"))
        whitelisted_checks = None

    Check.load(cis_path, solutions_path, whitelisted_checks)
    # Check.class_repr()
    # exit()

    exception = None
    try:
        Check.check_all()
    except Exception as exc:
        exception = exc

    if reboot_required:
        print(FormatText.blink("Reboot is required"))

    if exception is not None:
        raise exception

    print("\nExited.")
