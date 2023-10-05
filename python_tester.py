import argparse
import copy
import json
import sys
import types
import shutil
import signal

from io import StringIO

sys.dont_write_bytecode = True
graph_based = ["breadth_first_search",
               "depth_first_search",
               "detect_cycle",
               "minimum_spanning_tree",
               "reverse_linked_list",
               "shortest_path_length",
               "shortest_path_lengths",
               "shortest_paths",
               "topological_ordering"
               ]


# Used for capturing stdout
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


def handler(signum, frame):
    raise Exception("Timeout")


def py_try(algo, *args):
    try:
        if "correct_python_programs." + algo in sys.modules:
            del sys.modules["correct_python_programs." + algo]  # hack to reload module
        # this is set even before the first import since its possible that side effects are in file
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5)  # give 5 seconds
        module = __import__("correct_python_programs." + algo)
        fx = getattr(module, algo)
        re = getattr(fx, algo)(*args)
        re = prettyprint(re)
        signal.alarm(0)  # cancel alarm
        return re
    except:
        return sys.exc_info()


def py_try_test(algo):
    try:
        if "correct_python_programs." + algo + "_test" in sys.modules:
            del sys.modules["correct_python_programs." + algo + "_test"]  # hack to reload module
            del sys.modules["correct_python_programs." + algo]  # need to reload submodules from test as well, classic
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(5)  # give 5 seconds
        correct_module = __import__("correct_python_programs." + algo + "_test")
        correct_fx = getattr(correct_module, algo + "_test")
        output = []
        with Capturing(output) as output:  # need to do this because main has no output ... :(
            getattr(correct_fx, "main")()
        signal.alarm(0)  # cancel alarm
        return ["\n".join(output)]
    except:
        return sys.exc_info()


def prettyprint(o):
    if isinstance(o, types.GeneratorType):
        return "(generator) " + str(list(o))
    else:
        return str(o)


def move_file_and_copy(src, dest, prefix, postfix):
    with open(src, 'r') as f:
        s = f.read()
    shutil.copy(dest, dest + ".bak")
    with open(dest, 'w') as f:
        if prefix is not None and postfix is not None:
            f.write(prefix + s + postfix)
        else:
            f.write(s)


def main():
    parser = argparse.ArgumentParser(description="Tester Python")
    # TODO add option to add just a single line since we already know the location of the bug to be replaced
    parser.add_argument('--bug', type=str, help='bug to evaluate')
    parser.add_argument('--file', type=str, help='proposed fix in a file')
    parser.add_argument('--add_pf', action='store_true', default=False,
                        help='Use this in conjunction with --file to add the prefix and post fix to the file, '
                             'due to only considering functions we need to add additional code to run')

    args = parser.parse_args()
    print(args)
    correct = []
    patch = []
    prefix, postfix = None, None
    if args.add_pf:
        # load json from file
        with open("Python/pf.json", 'r') as f:
            data = json.load(f)
            if args.bug in data:
                prefix = data[args.bug]["prefix"]
                postfix = data[args.bug]["postfix"]

    if args.bug in graph_based:
        print("Running correct python:")
        correct = py_try_test(args.bug)
        print(correct[0])

        print("Running patch python:")
        move_file_and_copy(args.file, "correct_python_programs/{}.py".format(args.bug), prefix, postfix)
        patch = py_try_test(args.bug)
        print(patch[0])
        shutil.move("correct_python_programs/{}.py".format(args.bug) + ".bak",
                    "correct_python_programs/{}.py".format(args.bug))

    else:
        working_file = open("json_testcases/" + args.bug + ".json", 'r')

        for line in working_file:
            py_testcase = json.loads(line)
            print(py_testcase)
            test_in, test_out = py_testcase
            if not isinstance(test_in, list):
                test_in = [test_in]

            print("Running correct python:")
            c = py_try(args.bug, *copy.deepcopy(test_in))
            print(c)
            correct.append(c)

            print("Running patch python:")
            move_file_and_copy(args.file, "correct_python_programs/{}.py".format(args.bug), prefix, postfix)
            o = py_try(args.bug, *copy.deepcopy(test_in))
            print(o)
            patch.append(o)
            # whence you came
            shutil.move("correct_python_programs/{}.py".format(args.bug) + ".bak",
                        "correct_python_programs/{}.py".format(args.bug))
            if c != o:
                print("This is not a correct patch")
                sys.exit(1)

    if len(patch) != len(correct):
        print("This is not a correct patch")
        sys.exit(1)
    else:
        for i, _ in enumerate(patch):
            if patch[i] != correct[i]:
                print("This is not a correct patch")
                sys.exit(1)
        print("This is a plausible patch")
        sys.exit(0)


if __name__ == "__main__":
    main()
