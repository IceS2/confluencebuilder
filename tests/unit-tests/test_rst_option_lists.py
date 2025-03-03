# SPDX-License-Identifier: BSD-2-Clause
# Copyright Sphinx Confluence Builder Contributors (AUTHORS)

from tests.lib.parse import parse
from tests.lib.testcase import ConfluenceTestCase
from tests.lib.testcase import setup_builder
import os


class TestConfluenceRstOptionLists(ConfluenceTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dataset = os.path.join(cls.datasets, 'rst', 'option-lists')

    @setup_builder('confluence')
    def test_storage_rst_option_lists(self):
        out_dir = self.build(self.dataset)

        with parse('index', out_dir) as data:
            options_table = data.find('table')
            self.assertIsNotNone(options_table)

            rows = options_table.find_all('tr')
            self.assertEqual(len(rows), 6)

            for row in rows:
                cols = row.find_all('td')
                self.assertIsNotNone(cols)
                self.assertEqual(len(cols), 2)

                option_label = cols[0].find('code', recursive=False)
                self.assertIsNotNone(option_label)
                self.assertIsNotNone(option_label.contents)

                self.assertIsNotNone(cols[1].contents)

            # c flag with argument
            row = rows[2]
            emphasized_arg = row.find('em')
            self.assertIsNotNone(emphasized_arg)
            self.assertEqual(emphasized_arg.text, 'arg')

            # d flag with detailed description
            row = rows[3]
            detailed_list = row.find('ul')
            self.assertIsNotNone(detailed_list)

            # long-option with value
            row = rows[5]
            emphasized_arg = row.find('em')
            self.assertIsNotNone(emphasized_arg)
            self.assertEqual(emphasized_arg.text, 'value')
