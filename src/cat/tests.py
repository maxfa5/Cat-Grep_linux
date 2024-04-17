import logging
import argparse
import random
import string
import subprocess
from subprocess import CompletedProcess
from typing import Optional, List
from pathlib import Path
import enum
import difflib as df

logger = logging.getLogger(__name__)


def get_summary_of_work(total_cases: int, total_fails: int):
    fail_percents = (total_fails / total_cases) * 100
    if fail_percents < 3:
        return 'This is not a bug, this is an undocumented feature (:'
    if fail_percents < 10:
        return 'Already better son, left a little'
    if fail_percents < 30:
        return 'I see your efforts. there aren\'t enough of them'
    if fail_percents < 60:
        return 'McDonald\'s needs workers. Maybe you\'ll give it up?'
    if fail_percents < 80:
        return 'Looks like shit dude, stop message with girls and try to work'
    return 'Look like you need to work'


class Color(str, enum.Enum):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def warn(text: str, bold: Optional[bool] = False) -> str:
        return ''.join(filter(None, [
            Color.BOLD if bold else None,
            Color.WARNING,
            text,
            Color.ENDC
        ]))

    @staticmethod
    def fail(text: str, bold: Optional[bool] = False) -> str:
        return ''.join(filter(None, [
            Color.BOLD if bold else None,
            Color.FAIL,
            text,
            Color.ENDC
        ]))

    @staticmethod
    def success(text: str, bold: Optional[bool] = False, cyan: Optional[bool] = False) -> str:
        return ''.join(filter(None, [
            Color.BOLD if bold else None,
            Color.OKCYAN if cyan else Color.OKGREEN,
            text,
            Color.ENDC
        ]))

    @staticmethod
    def bold(text: str) -> str:
        return ''.join([Color.BOLD, text, Color.ENDC])

    @staticmethod
    def underline(text: str) -> str:
        return ''.join([Color.UNDERLINE, text, Color.ENDC])


class ExecutableProcess:
    name: str = None

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.name
        if not self.name:
            raise Exception('process name not specified')

    def exec(self, *args) -> CompletedProcess:
        logger.debug(f'run process: {self.name} {" ".join(args)}')
        return subprocess.run(
            [self.name, *args],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
            encoding="UTF-8",
        )


class Valgrind(ExecutableProcess):
    name = 'valgrind'

    def is_leak_exists(self, *args) -> bool:
        result = self.exec(*args)
        if 'HEAP SUMMARY' not in result.stdout:
            raise Exception(result.stdout)

        return 'LEAK SUMMARY' in result.stdout

    def is_installed(self) -> bool:
        try:
            result = self.exec('--help')
            return result.returncode == 0
        except FileNotFoundError:
            return False


class Cat(ExecutableProcess):
    name = 'cat'


class S21CatProcess(ExecutableProcess):
    name = './s21_cat'


class Matcher:
    def __init__(self, use_valgrind: bool = False, max_diff_count: int = 8):
        self.use_valgrind = use_valgrind
        self.max_diff_count = max_diff_count

    def match(self, *cmd_args) -> bool:
        cat = Cat()
        s21_cat = S21CatProcess()

        test_name = ' '.join([s21_cat.name, *cmd_args])

        print('{:<6} {}\r'.format('RUN', test_name), end='')

        cat_result = cat.exec(*cmd_args)
        s21_cat_result = s21_cat.exec(*cmd_args)

        memory_leaks = False
        if self.use_valgrind:
            memory_leaks = Valgrind().is_leak_exists(*s21_cat_result.args)

        is_success = not memory_leaks and self.is_match(cat_result, s21_cat_result)

        if is_success:
            print('{:<6} {}'.format(Color.success('PASSED', bold=True), Color.success(test_name)))
        else:
            print('{:<6} {}'.format(Color.fail('FAILED', bold=True), Color.fail(test_name)))
            if memory_leaks:
                print(Color.warn(f'└─ memory leaks (use "valgrind {" ".join(s21_cat_result.args)}" for detail)'))

            if cat_result.returncode != s21_cat_result.returncode:
                print(Color.warn(f'└─ not equal return code'))
                print(Color.warn(f'  └─ cat return code: {cat_result.returncode}'))
                print(Color.warn(f'  └─ s21_cat return code: {s21_cat_result.returncode}'))

            if cat_result.stdout != s21_cat_result.stdout:
                print(Color.warn(' '.join(filter(None, [
                    '└─ stdout is not equal',
                    '(you out is empty)' if (cat_result.stdout and not s21_cat_result.stdout) else None
                ]))))
                self.show_differences(cat_result.stdout, s21_cat_result.stdout, self.max_diff_count)

            if cat_result.stderr != s21_cat_result.stderr:
                print(Color.warn(' '.join(filter(None, [
                    '└─ stderr is not equal',
                    '(you out is empty)' if (cat_result.stderr and not s21_cat_result.stderr) else None
                ]))))
                self.show_differences(cat_result.stderr, s21_cat_result.stderr, self.max_diff_count)
            print('\n')

        return is_success

    def is_match(self, cat_result: CompletedProcess, s21_cat: CompletedProcess) -> bool:
        return all([
            cat_result.returncode == s21_cat.returncode,
            cat_result.stdout == s21_cat.stdout,
            cat_result.stderr == s21_cat.stderr  # not tested
        ])

    @staticmethod
    def show_differences(cat: str, s21_cat: str, max_length: int = 4):
        diff = df.Differ().compare(cat.splitlines(), s21_cat.splitlines())

        legend_items: List[str] = []

        cat_result_legend = Color.success('[-] cat')
        s21_cat_result_legend = Color.fail('[+] s21_cat')
        match_result_legend = Color.success('[?] match', cyan=True)

        rows: List[str] = []

        for row in diff:
            if row.startswith('+'):
                rows.append(Color.fail(row))
                if s21_cat_result_legend not in legend_items:
                    legend_items.append(s21_cat_result_legend)

            if row.startswith('-'):
                rows.append(Color.success(row))
                if cat_result_legend not in legend_items:
                    legend_items.append(cat_result_legend)

            if row.startswith('?'):
                rows.append(Color.success(row, cyan=True))
                if match_result_legend not in legend_items:
                    legend_items.append(match_result_legend)

            if max_length and (len(rows) >= max_length):
                rows.append(f'... (отображаются первые {max_length})')
                break

        if rows:
            if legend_items:
                print(f'    {" | ".join(legend_items)}')
            for row in rows:
                print(f'    └ {row}')

    def start_compare(self, run_options: List[List[str]]) -> int:
        fails = 0
        for options in run_options:
            if not self.match(*options):
                fails += 1
        return fails


def ensure_files(*args):
    defaults = {
        'text_ru.txt': {
            'text': [
                'Однажды на улице была сильная гроза.',
                'Пупа и Лупа очень испугались грома и решили спрятаться от него под деревом.',
                'Они обнялись и стали рассказывать друг другу страшные истории.',
                'Но вдруг они услышали странный звук. Это был звук, похожий на смех.',
                'Пупа и Лупа посмотрели друг на друга и увидели маленького белого кролика, который смеялся над ними.'
                'Он сказал им: «Не бойтесь грома, он не причинит вам вреда».',
                'И тогда Пупа и Лупа перестали бояться грома и продолжили играть вместе.'
            ],
        },
        'text_en.txt': {
            'text': [
                '1  1\t22%% %',
                '\n\n',
                '4 \t\t4',
                'Simple is better than complex',
                'Complex is better than complicated.',
                'Flat is better than nested.',
                'Sparse is better than dense.',
            ],
        },
        'text_empty.txt': {
            'text': []
        },
        'text_punc.txt': {
            'text': [
                ' '.join([
                    f'{i}_{random.choice(string.punctuation)}' for i in range(random.randint(8, 24))
                ]) for _ in range(16)
            ]
        }
    }

    def gen_text(filename: str, rows: List[str]):
        print(Color.warn(f'iam generate new file: {filename}'))
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rows))

    for file in args:
        if not Path(file).exists():
            if file not in defaults:
                raise Exception(f'File {file} does not exist')
            gen_text(file, defaults.get(file).get('text'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true', default=False)
    parser.add_argument('-v', '--valgrind', help='enable memory check', action='store_true', default=False)
    config = parser.parse_args()

    if config.debug:
        logging.basicConfig(level=logging.DEBUG)

    use_valgrind = config.valgrind
    if use_valgrind and not Valgrind().is_installed():
        use_valgrind = False
        print(Color.warn('valgrind is not installed. skip memory leak checks..'))

    # runnable options
    short_opts = ['-b', '-e', '-n', '-s', '-t', '-T', '-v']
    long_opts = [
        '--number-nonblank',
        '--number',
        '--squeeze-blank',
        # '--unsupported-flag',
        # '--help',
    ]
    filenames = [
        'text_en.txt',
        'text_ru.txt',
        'text_punc.txt',
        'text_empty.txt',
        # your own file.txt
    ]
    ensure_files(*filenames)

    runnable_options = [[filename] for filename in filenames]
    runnable_options += [[o, filename] for o in short_opts for filename in filenames]
    runnable_options += [[filename, o] for o in short_opts for filename in filenames]
    runnable_options += [[o, filename] for o in long_opts for filename in filenames]
    runnable_options += [[filename, o] for o in long_opts for filename in filenames]

    total_cases = len(runnable_options)
    print(' '.join([
        f'Total cases: {total_cases}',
        f'valgrind-check: {"enabled" if use_valgrind else "disabled"}'
    ]))

    matcher = Matcher(use_valgrind=use_valgrind)
    total_fails = matcher.start_compare(runnable_options)

    if total_fails:
        print(' '.join([
            Color.fail(f'Total fails: {total_fails}/{len(runnable_options)}'),
            get_summary_of_work(total_cases, total_fails)
        ]))

    else:
        print(Color.success('Looks good *thumb_up*, lets see what valgrind-penetrator says'))
