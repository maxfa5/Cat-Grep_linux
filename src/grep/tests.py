import itertools
import logging
import argparse
import subprocess
import time
import enum
import difflib as df
from dataclasses import dataclass
from functools import reduce
from subprocess import CompletedProcess
from typing import Optional, List
from pathlib import Path
 
 
logger = logging.getLogger(__name__)
 
 
class StopTestException(Exception):
    ...
 
 
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
            str(text),
            Color.ENDC
        ]))
 
    @staticmethod
    def fail(text: str, bold: Optional[bool] = False) -> str:
        return ''.join(filter(None, [
            Color.BOLD if bold else None,
            Color.FAIL,
            str(text),
            Color.ENDC
        ]))
 
    @staticmethod
    def success(text: str, bold: Optional[bool] = False, cyan: Optional[bool] = False) -> str:
        return ''.join(filter(None, [
            Color.BOLD if bold else None,
            Color.OKCYAN if cyan else Color.OKGREEN,
            str(text),
            Color.ENDC
        ]))
 
    @staticmethod
    def bold(text: str) -> str:
        return ''.join([Color.BOLD, str(text), Color.ENDC])
 
    @staticmethod
    def underline(text: str) -> str:
        return ''.join([Color.UNDERLINE, str(text), Color.ENDC])
 
 
class ExecutableProcess:
    name: str = None
 
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.name
        assert self.name, 'process name not specified'
 
    def exec(self, *args) -> CompletedProcess:
        logger.debug(f'run process: {self.name} {" ".join(args)}')
        start = time.perf_counter()
        result = subprocess.run(
            [self.name, *args],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
            encoding="UTF-8",
        )
        setattr(result, 'processed_time', round(time.perf_counter() - start, 3))
        return result
 
 
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
 
 
class Grep(ExecutableProcess):
    name = 'grep'
 
 
class S21Grep(ExecutableProcess):
    name = './s21_grep'
    # name = 'grep'
 
 
@dataclass
class MatchResult:
    grep_processed_time: float
    s21_grep_processed_time: float
 
    is_success: bool = False
 
 
class Matcher:
    def __init__(self, use_valgrind: bool = False, max_diff_count: Optional[int] = None, stop_on_fail: bool = False):
        self.use_valgrind = use_valgrind
        self.max_diff_count = max_diff_count
        self.stop_on_fail = stop_on_fail
 
    def match(self, *cmd_args) -> MatchResult:
        grep = Grep()
        s21_grep = S21Grep()
 
        test_name = ' '.join([s21_grep.name, *cmd_args])
        logger.debug(' '.join(['use args', '{}'.format(list(cmd_args))]))
 
        grep_result = grep.exec(*cmd_args)
 
        s21_grep_result = s21_grep.exec(*cmd_args)
 
        memory_leaks = False
        if self.use_valgrind:
            memory_leaks = Valgrind().is_leak_exists(*s21_grep_result.args)
 
        is_success = not memory_leaks and self.is_match(grep_result, s21_grep_result)
        if is_success:
            print(Color.success('{:<8} {}'.format('PASSED', test_name), bold=True))
        else:
            print(Color.fail('{:<8} {}'.format('FAILED', test_name), bold=True))
 
            if memory_leaks:
                print(Color.warn(f'└─ memory leaks (use "valgrind {" ".join(s21_grep_result.args)}" for detail)'))
            if grep_result.returncode != s21_grep_result.returncode:
                print(Color.warn(f'└─ not equal return code'))
                print(Color.warn(f'  ├─ {grep.name} return code: {grep_result.returncode}'))
                print(Color.warn(f'  └─ {s21_grep.name} return code: {s21_grep_result.returncode}'))
            if grep_result.stdout != s21_grep_result.stdout:
                print(Color.warn(' '.join(filter(None, [
                    '└─ stdout is not equal',
                    '(you out is empty)' if (grep_result.stdout and not s21_grep_result.stdout) else None
                ]))))
                self.show_differences(grep_result.stdout, s21_grep_result.stdout, self.max_diff_count)
            if grep_result.stderr != s21_grep_result.stderr:
                print(Color.warn(' '.join(filter(None, [
                    '└─ stderr is not equal',
                    '(you out is empty)' if (grep_result.stderr and not s21_grep_result.stderr) else None
                ]))))
                self.show_differences(grep_result.stderr, s21_grep_result.stderr, self.max_diff_count)
 
        return MatchResult(
            grep_processed_time=getattr(grep_result, 'processed_time', None),
            s21_grep_processed_time=getattr(s21_grep_result, 'processed_time', None),
            is_success=is_success
        )
 
    def is_match(self, grep_result: CompletedProcess, s21_grep_result: CompletedProcess) -> bool:
        return all([
            grep_result.returncode == s21_grep_result.returncode,
            grep_result.stdout == s21_grep_result.stdout,
            grep_result.stderr == s21_grep_result.stderr  # not tested
        ])
 
    @staticmethod
    def show_differences(cat: str, s21_cat: str, max_length: Optional[int] = None):
        diff = df.Differ().compare(cat.splitlines(), s21_cat.splitlines())
 
        legend_items: List[str] = []
 
        # cat_result_legend = Color.success('[-] grep')
        # s21_cat_result_legend = Color.fail('[+] s21_grep')
        cat_result_legend = '[-] grep'
        s21_cat_result_legend = '[+] s21_grep'
        match_result_legend = Color.success('[?] match', cyan=True)
 
        rows: List[str] = []
        for row in diff:
            if row.startswith('+'):
                # rows.append(Color.fail(row))
                rows.append(row)
                if s21_cat_result_legend not in legend_items:
                    legend_items.append(s21_cat_result_legend)
            if row.startswith('-'):
                # rows.append(Color.success(row))
                rows.append(row)
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
 
    def start_compare(self, run_options: List[List[str]]) -> List[MatchResult]:
        total = len(run_options)
        all_results = []
        for i, options in enumerate(run_options):
            print('{:<12} {}'.format(f'RUN [{i}/{total}]', ' '.join([*options])), end='\r')
            result: MatchResult = self.match(*options)
            if self.stop_on_fail and not result.is_success:
                raise StopTestException
            all_results.append(result)
 
        return all_results
 
 
def ensure_files(*args):
    defaults = {
        'text_1.txt': {
            'text': [
                'lower registry',
                'lower registry',
                'lower registry2',
                '',
                'lower registry3',
            ]
        },
        'text_2.txt': {
            'text': [
                'UPPER REGISTRY',
                'UPPER REGISTRY',
                'UPPER REGISTRY1',
                '',
                'UPPER REGISTRY2'
            ]
        },
        'text_empty.txt': {
            'text': []
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
 
 
def get_message_from_testman(total_cases: int, total_fails: int) -> str:
    if not total_fails:
        return Color.success('geek brain! *thumb_up*, lets see what valgrind-penetrator says')
 
    fail_percents = round((total_fails / total_cases) * 100, 2)
    fail_percents_text = f'{fail_percents}%'
 
    if fail_percents <= 3:
        message = f'This is not a bug, this is an undocumented feature (:'
        fail_percents_text = Color.warn(f'{fail_percents}%')
    elif fail_percents <= 10:
        message = 'Already better son, left a little'
        fail_percents_text = Color.warn(f'{fail_percents}%')
    elif fail_percents <= 33:
        message = 'I see your efforts. there aren\'t enough of them'
        fail_percents_text = Color.warn(f'{fail_percents}%')
    elif fail_percents <= 66:
        message = 'McDonald\'s needs workers. Maybe you\'ll give it up?'
        fail_percents_text = Color.fail(f'{fail_percents}%')
    elif 66 < fail_percents:
        message = 'Looks like shit dude, stop message with girls and try to work'
        fail_percents_text = Color.fail(f'{fail_percents}%')
    else:
        message = 'Looks like u need to work'
 
    return ' '.join([
        f'Total fails: {total_fails}/{total_cases}',
        f'({fail_percents_text})',
        message
    ])
 
 
def calculate_performance(result: list[MatchResult]) -> list[str]:
    grep_processed_time = reduce(lambda a, b: a + b, [i.grep_processed_time for i in result])
    s21_grep_processed_time = reduce(lambda a, b: a + b, [i.s21_grep_processed_time for i in result])
 
    if s21_grep_processed_time < grep_processed_time:
        perc_changed = round((abs(grep_processed_time - s21_grep_processed_time) / s21_grep_processed_time) * 100.0, 2)
        perf_message = Color.success(' '.join([
            'faster by',
            Color.success(f'{perc_changed}%', bold=True)
        ]))
    else:
        perc_changed = round((abs(s21_grep_processed_time - grep_processed_time) / grep_processed_time) * 100.0, 2)
        perf_message = Color.fail(' '.join([
            'slower by',
            Color.fail(f'{perc_changed}%', bold=True)
        ]))
    return [
        f'grep processed time: {round(grep_processed_time, 2)} sec.',
        f's21_grep processed time: {round(s21_grep_processed_time, 2)} sec. ({perf_message})',
    ]
 
 
def create_multi_arguments(opts: List[str], templates: List[str], filenames: List[str]) -> List[List[str]]:
    opts_combinations = []
    for i in range(1, len(opts)):
        opts_combinations.extend(itertools.combinations(opts, i))
 
    filenames_combinations = []
    for i in range(1, len(filenames)):
        filenames_combinations.extend(itertools.combinations(filenames, i))
 
    multi_args = [
        [*opt, template, *files]
        for opt in opts_combinations
        for template in templates
        for files in filenames_combinations
    ]
    return multi_args
 
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true', default=False)
    parser.add_argument('-v', '--valgrind', help='enable memory check', action='store_true', default=False)
    parser.add_argument('-m', '--multi', help='check for multi flags', action='store_true', default=False)
    parser.add_argument('-s', '--stop-on-fail', help='stop check on first fail', action='store_true', default=False)
    config = parser.parse_args()
 
    logging.basicConfig(level=logging.DEBUG if config.debug else logging.WARN)
 
    use_valgrind = config.valgrind
    if use_valgrind and not Valgrind().is_installed():
        use_valgrind = False
        print(Color.warn('valgrind is not installed. skip memory leak checks..'))
 
    # runnable options
    filenames = [
        'text_1.txt',
        'text_2.txt',
        'text_empty.txt'
        # your own file.txt
    ]
    ensure_files(*filenames)
 
    short_opts = ['-i', '-v', '-c', '-l', '-n', '-o', '-h']
    searchable_templates = [
        'registry',
        'REGISTRY',
        'reg$'
    ]
    runnable_options: List[List[str]] = []
    runnable_options.extend(itertools.chain(
        # [options] template [file_name]
        itertools.product(short_opts, searchable_templates, filenames),
 
        # template [options] [file_name]
        itertools.product(searchable_templates, short_opts, filenames),
 
        # [options] -e <template> [file_name]
        itertools.product(short_opts, [f'-e {tmp}' for tmp in searchable_templates], filenames),
 
        # -e <template> [options] [file_name]
        itertools.product([f'-e {tmp}' for tmp in searchable_templates], short_opts, filenames)
    ))
 
    if config.multi:
        multi_runnable_options: List[List[str]] = list(filter(
            lambda opts: opts not in runnable_options,
            create_multi_arguments(short_opts, searchable_templates, filenames)
        ))
        if input(' '.join([
            f'Type "y/Y" if you rly wanna',
            Color.warn(f'add {len(multi_runnable_options)} tests'),
            f'for you little {S21Grep.name.lstrip("./")}?',
            f'Total tests-cases will be {len(runnable_options) + len(multi_runnable_options)}\n'
        ])) in ['y', 'Y']:
            runnable_options.extend(multi_runnable_options)
 
    total_cases = len(runnable_options)
    print(' '.join([
        f'Total cases: {total_cases}',
        f'valgrind-check: {"enabled" if use_valgrind else "disabled"}'
    ]))
 
    matcher = Matcher(use_valgrind=use_valgrind, max_diff_count=8, stop_on_fail=config.stop_on_fail)
    try:
        match_results: List[MatchResult] = matcher.start_compare(runnable_options)
        print(' '.join(calculate_performance(match_results)))
 
        total_fails = len(list(filter(lambda r: not r.is_success, match_results)))
        print(get_message_from_testman(total_cases, total_fails))
 
    except StopTestException:
        print('Stopped on first fail')