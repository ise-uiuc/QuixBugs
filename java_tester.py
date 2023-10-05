import argparse
import copy
import json
import shutil
import sys
import subprocess
import types

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


def prettyprint(o):
    if isinstance(o, types.GeneratorType):
        return ("(generator) " + str(list(o)))
    else:
        return (str(o))


def run_java_test(test_in, algo, test=False, compile=True):
    if compile:
        cmd = 'cd /home/steven/llm/QuixBugs/; gradle build --rerun-tasks'
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print("Return code: {}".format(e.returncode))
            return False, None
    try:
        if not test and algo != "wrap" and algo != "is_valid_parenthesization":
            print('cd /home/steven/llm/QuixBugs/build/classes/java/main/; /usr/bin/java JavaDeserialization '
                + algo + ' "' + '" "'.join([json.dumps(arg) for arg in copy.deepcopy(test_in)]) + '"')
            p1 = subprocess.run(
                'cd /home/steven/llm/QuixBugs/build/classes/java/main/; /usr/bin/java JavaDeserialization '
                + algo + ' "' + '" "'.join([json.dumps(arg) for arg in copy.deepcopy(test_in)]) + '"',
                shell=True, capture_output=True, text=True, timeout=5)
            java_out = p1.stdout
            return True, prettyprint(java_out)
        elif algo == "wrap" or algo == "is_valid_parenthesization":
            p1 = subprocess.run(
                'cd /home/steven/llm/QuixBugs/build/classes/java/main/; /usr/bin/java JavaDeserialization '
                + algo + " '" + "' '".join([json.dumps(arg) for arg in copy.deepcopy(test_in)]) + "'",
                shell=True, capture_output=True, text=True, timeout=5)
            java_out = p1.stdout
            return True, prettyprint(java_out)
        else:
            p1 = subprocess.run(
                'cd build/classes/java/main/java_testcases; /usr/bin/java -cp ../ java_testcases.' + algo.upper() + '_TEST',
                shell=True, capture_output=True, text=True, timeout=5)
            java_out = p1.stdout
            return True, prettyprint(java_out)
    except:
        subprocess.run(["ps -ef | grep 'JavaDeserialization' | grep -v grep | awk '{print $2}' | xargs -r kill -9"],
               shell=True)  # kill all tests thank you
        subprocess.run(["ps -ef | grep 'java_testcases.' | grep -v grep | awk '{print $2}' | xargs -r kill -9"],
                       shell=True)  # kill all tests thank you
        return False, prettyprint(sys.exc_info())


def move_file_and_copy(src, dest, prefix, postfix):
    with open(src, 'r') as f:
        s = f.read()
    shutil.copy(dest, dest + ".bak")
    with open(dest, 'w') as f:
        print(prefix + "\n" + s + "\n" + postfix)
        if prefix is not None and postfix is not None:
            f.write(prefix + "\n" + s + "\n" + postfix)
        else:
            f.write(s)


def main():
    parser = argparse.ArgumentParser(description="Tester Java")
    # TODO add option to add just a single line since we already know the location of the bug to be replaced
    parser.add_argument('--bug', type=str, help='bug to evaluate')
    parser.add_argument('--file', type=str, help='proposed fix in a file')
    parser.add_argument('--add_pf', action='store_true', default=False,
                        help='Use this in conjunction with --file to add the prefix and post fix to the file, '
                             'due to only considering functions we need to add additional code to run')

    args = parser.parse_args()
    print(args)

    if args.add_pf:
        # load json from file
        with open("Java/pf.json", "r") as f:
            data = json.load(f)
            prefix = data[args.bug]['prefix']
            postfix = data[args.bug]['postfix']

    with open("Java/test_out.json", "r") as f:
        data = json.load(f)
        correct = data[args.bug]

    patch = []

    if args.bug in graph_based:
        move_file_and_copy(args.file, "java_programs/{}.java".format(args.bug.upper()), prefix, postfix)
        subprocess.run("touch -d '12 December' " + "java_programs/{}.java".format(args.bug.upper()), shell=True)
        compiled, o = run_java_test("", args.bug, test=True, compile=True)
        shutil.move("java_programs/{}.java".format(args.bug.upper()) + ".bak",
                    "java_programs/{}.java".format(args.bug.upper()))
        if not compiled:
            sys.exit(1)
        patch.append(o)
    else:
        working_file = open("json_testcases/" + args.bug + ".json", 'r')
        index = 0
        move_file_and_copy(args.file, "java_programs/{}.java".format(args.bug.upper()), prefix, postfix)
        subprocess.run("touch -d '12 December' " + "java_programs/{}.java".format(args.bug.upper()), shell=True)
        for line in working_file:
            py_testcase = json.loads(line)
            print(py_testcase)
            test_in, test_out = py_testcase
            if not isinstance(test_in, list):
                # input is required to be a list, as multiparameter algos need to deconstruct a list of parameters
                # should fix in testcases, force all inputs to be list of inputs
                test_in = [test_in]
                # unsure how to make immutable; previous versions just used copy.deepcopy
            print(test_in)
            compiled, o = run_java_test(test_in, args.bug, compile=index==0)
            if not compiled:
                shutil.move("java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "java_programs/{}.java".format(args.bug.upper()))
                sys.exit(1)
            print(o)
            if correct[index] != o:
                print("This is not a correct patch")
                shutil.move("java_programs/{}.java".format(args.bug.upper()) + ".bak",
                            "java_programs/{}.java".format(args.bug.upper()))
                sys.exit(1)
            patch.append(o)
            index += 1
        shutil.move("java_programs/{}.java".format(args.bug.upper()) + ".bak",
                    "java_programs/{}.java".format(args.bug.upper()))

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