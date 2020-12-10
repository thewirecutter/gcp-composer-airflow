# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from abc import ABCMeta
from typing import List
import json

import pygments
from pygments.console import colorize
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers.markup import RstLexer

from airflow.upgrade.problem import RuleStatus
from airflow.upgrade.rules.base_rule import BaseRule
from airflow.utils.cli import header, get_terminal_size


class BaseFormatter(object):
    __metaclass__ = ABCMeta

    def start_checking(self, all_rules):
        # type: (List[BaseRule]) -> None
        pass

    def end_checking(self, rule_statuses):
        # type: (List[RuleStatus]) -> None

        pass

    def on_next_rule_status(self, rule_status):
        # type: (RuleStatus) -> None
        pass


class ConsoleFormatter(BaseFormatter):
    def start_checking(self, all_rules):
        print()
        header("STATUS", "=")
        print()

    def end_checking(self, rule_statuses):
        messages_count = sum(
            len(rule_status.messages)
            for rule_status in rule_statuses
        )
        if messages_count == 1:
            print("Found {} problem.".format(messages_count))
        else:
            print("Found {} problems.".format(messages_count))
        print()

        if messages_count > 0:
            header("RECOMMENDATIONS", "=")
            print()
            self.display_recommendations(rule_statuses)
        else:
            print("Not found any problems. World is beautiful. ")
            print("You can safely update Airflow to the new version.")

    @staticmethod
    def display_recommendations(rule_statuses):
        for rule_status in rule_statuses:
            # Show recommendations only if there are any messaged
            if not rule_status.messages:
                continue

            rule = rule_status.rule
            lines = [rule.title, "-" * len(rule.title)]
            if rule_status.skipped:
                lines.extend([rule_status.messages[0]])
            else:
                if rule.description:
                    lines.extend([rule.description])
                lines.extend([
                    "",
                    "Problems:",
                    "",
                ])
                lines.extend(['{:>3}.  {}'.format(i, m) for i, m in enumerate(rule_status.messages, 1)])
            msg = "\n".join(lines)

            formatted_msg = pygments.highlight(
                code=msg, formatter=TerminalFormatter(), lexer=RstLexer()
            )
            print(formatted_msg)

    def on_next_rule_status(self, rule_status):
        if rule_status.skipped:
            status = colorize("yellow", "SKIPPED")
        elif rule_status.is_success:
            status = colorize("green", "SUCCESS")
        else:
            status = colorize("red", "FAIL")
        status_line_fmt = self.prepare_status_line_format()
        print(status_line_fmt.format(rule_status.rule.title, status))

    @staticmethod
    def prepare_status_line_format():
        _, terminal_width = get_terminal_size()

        return "{:.<" + str(terminal_width - 10) + "}{:.>10}"


class JSONFormatter(BaseFormatter):
    def __init__(self, output_path):
        self.filename = output_path

    def start_checking(self, all_rules):
        print("Start looking for problems.")

    @staticmethod
    def _info_from_rule_status(rule_status):
        return {
            "rule": type(rule_status.rule).__name__,
            "title": rule_status.rule.title,
            "messages": rule_status.messages,
        }

    def end_checking(self, rule_statuses):
        formatted_results = [self._info_from_rule_status(rs) for rs in rule_statuses]
        with open(self.filename, "w+") as output_file:
            json.dump(formatted_results, output_file, indent=2)
        print("Saved result to: {}".format(self.filename))
