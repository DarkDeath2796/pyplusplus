import os
import re
import sys
import subprocess
import shutil
import uuid
from typing import List, Set, Optional


def print_progress(done: int, total: int) -> None:
    bar_length = 60
    filled_length = int(round(done / total * bar_length))
    percent = round(done / total * 100, 2)
    bar = '>' * filled_length + ' ' * (bar_length - filled_length)
    sys.stdout.write(f'\r[{bar}] {percent}%')
    sys.stdout.flush()

    if done == total:
        sys.stdout.write('\n')


def add_to_path_win(target_dir: str):
    subprocess.run(
        [
            "powershell",
            "-Command",
            f'[Environment]::SetEnvironmentVariable("Path", $env:Path + ";{target_dir}", "User")',
        ],
        shell=True,
    )


def setup_install(target_dir: str):
    os.makedirs(os.path.join(target_dir, "modules"), exist_ok=True)

    builtins = {
        "modules/std/fileOps.pypp": """
#include <fstream>
#include <vector>

fn read_file(const std::string &path) -> std::string
    std::ifstream f(path)
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
end

fn write_file(const std::string &path, const std::string &content) -> void
    std::ofstream f(path)
    f << content
end

fn read_lines(const std::string &path) -> strvec
    std::ifstream f(path)
    if !f.is_open()
        print("Failed to open file: ", path, "\\n")
        return {};
    end

    strvec lines
    std::string line
    while std::getline(f, line)
        line.erase(std::remove(line.begin(), line.end(), '\\r'), line.end())
        lines.push_back(line)
    end
    return lines
end

fn appnd_to_file(const std::string &path, const std::string &content) -> void
    std::ofstream f(path, std::ios::app)
    f << content
end
""",
        "modules/std/time.pypp": """
#include <chrono>
#include <thread>
#include <ctime>
#include <sstream>
#include <iomanip>

fn now_() -> double
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count()
end

fn sleep(double seconds) -> void
    std::this_thread::sleep_for(std::chrono::duration<double>(seconds));
end

fn since(double start) -> double
    return now_() - start
end

fn format(const std::string& fmt) -> std::string
    std::time_t t = std::time(nullptr);
    std::tm tm = *std::localtime(&t);
    std::ostringstream oss;
    oss << std::put_time(&tm, fmt.c_str());
    return oss.str()
end

fn wait_until(double target) -> void
    double diff = target - now_();
    if diff > 0
        sleep(diff)
    end
end
""",
        "modules/std/random.pypp": """
#include <cmath>
imp std/time.pypp


fn rand01() -> double
    double __seed = fmod(time_now_() * 6364136223846793005.0 * time_since(1) + 1.0, 1e9)
    return fmod(__seed / 1e9, 1.0)
end

fn randint(int a, int b) -> int
    return a + (int)(rand01() * (b - a + 1))
end

fn uniform(double a, double b) -> double
    return a + rand01() * (b - a)
end

fn randlen(int length) -> int
    if length <= 0
        return 0
    end
    int num = randint(1, 9); 
    for (int i = 1; i < length; i++) {
        int digit = randint(0, 9);
        num = num * 10 + digit;
    }
    return num
end
""",
        "modules/std/sys.pypp": """
#include <string>

#ifdef _WIN32
#include <windows.h>
#include <locale>
#include <codecvt>
#endif

fn get_username() -> std::string
#ifdef _WIN32
    wchar_t buffer[256];
    DWORD size = 256;
    if (GetUserNameW(buffer, &size))
        std::wstring_convert<std::codecvt_utf8<wchar_t>> conv;
        return conv.to_bytes(buffer);
    else
        return "???"
    end
#else
    const char* user = std::getenv("USER");
    return user ? std::string(user) : "???"
#endif
end
""",
        "modules/std/strOps.pypp": """
#include <algorithm>
#include <cctype>
#include <string>

fn trim(const std::string& s) -> std::string
    size_t start = 0
    while start < s.size() && std::isspace(s[start]) 
        start++
    end
    size_t end = s.size()
    while end > start && std::isspace(s[end - 1])
        end--
    end
    return s.substr(start, end - start)
end

fn lower(std::string s) -> std::string
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::tolower(c); });
    return s
end

fn upper(std::string s) -> std::string
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::toupper(c); });
    return s
end

fn split(const std::string& s, char delimiter) -> strvec
    strvec result;
    size_t start = 0, end;
    while (end = s.find(delimiter, start)) != std::string::npos
        result.push_back(s.substr(start, end - start));
        start = end + 1;
    end
    result.push_back(s.substr(start));
    return result;
end
""",
        "modules/std/__init__.pypp": """
imp std/fileOps.pypp
imp std/time.pypp
imp std/random.pypp
imp std/strOps.pypp
imp std/sys.pypp
""",
    }

    # Write built-in modules
    for rel, content in builtins.items():
        path = os.path.join(target_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # Detect mode (exe or script)
    if getattr(sys, "frozen", False):
        self_path = sys.executable
    else:
        self_path = os.path.abspath(sys.argv[0])

    dest = os.path.join(target_dir, os.path.basename(self_path))
    if os.path.abspath(self_path) != os.path.abspath(dest):
        try:
            shutil.copy2(self_path, dest)
            print(f"[+] Copied installer to {dest}")
        except Exception as e:
            print(f"[!] Could not copy self: {e}")

    # Add to PATH only if not already there
    path_env = os.environ.get("PATH", "")
    paths = [p.strip() for p in path_env.split(os.pathsep)]
    if target_dir not in paths:
        if os.name == "nt":
            add_to_path_win(target_dir)
            print(f"[+] Added {target_dir} to PATH")
        else:
            print(f"[*] Add {target_dir} to PATH with 'export PATH={target_dir}:$PATH'")
            print("Sorry, adding to PATH is not supported on this platform :(")
    else:
        print(f"[*] {target_dir} already in PATH, skipping")

    print(f"\n[+] Py++ installed to: {target_dir}")
    print("[*] Restart your terminal to use the 'py++' command globally!\n")


def check_gpp_installed() -> bool:
    try:
        result = subprocess.run(
            ["g++", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
#  Import logic: recursively load modules with renamed symbols
# ---------------------------------------------------------------------------


def safe_replace(line: str, name: str, replacement: str) -> str:
    if line.lstrip().startswith("%>"):  # full-line comment
        return line

    new_line = ""
    i = 0
    in_str = False
    while i < len(line):
        c = line[i]
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
            new_line += c
            i += 1
            continue
        if in_str:
            new_line += c
            i += 1
            continue

        # try to match the function name as a standalone token
        if line[i : i + len(name)] == name:
            before = line[i - 1] if i > 0 else " "
            after = line[i + len(name)] if i + len(name) < len(line) else " "
            if (
                not before.isalnum()
                and before != "_"
                and not after.isalnum()
                and after != "_"
            ):
                new_line += replacement
                i += len(name)
                continue

        new_line += c
        i += 1
    return new_line


def load_with_imports_renamed(
    path: str,
    loaded: Optional[Set[str]] = None,
    base_dir: Optional[str] = None,
    is_main: bool = True,
):
    if loaded is None:
        loaded = set()

    # exe dir (global modules)
    exe_dir = os.path.dirname(
        sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    )

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(path))

    norm_path = os.path.abspath(path)
    if norm_path in loaded:
        return ""
    loaded.add(norm_path)

    if not os.path.exists(path):
        print(f"[Py++] Error: file '{path}' not found")
        sys.exit(404)

    with open(path, "r", encoding="utf-8") as f:
        raw_src = f.read()

    src = preprocess_defines(raw_src)
    out_lines = []

    mod_name = None if is_main else os.path.splitext(os.path.basename(path))[0]
    func_names, var_names = [], []

    if mod_name:
        print(f"Importing {mod_name}", end="\r")

    lines = src.splitlines()
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("imp "):
            imp_target = stripped[4:].strip()

            # 1️⃣ check exe_dir/modules
            submod_path = os.path.join(exe_dir, "modules", imp_target)
            # 2️⃣ check in standard installation directory C:\pypp (where setup installs)
            if not os.path.exists(submod_path):
                standard_install_path = r"C:\pypp"
                submod_path = os.path.join(
                    standard_install_path, "modules", imp_target
                )
            # 3️⃣ fallback to local directory of current file
            if not os.path.exists(submod_path):
                submod_path = os.path.join(base_dir, imp_target)

            if os.path.exists(submod_path):
                # if the submodule is a directory
                if os.path.isdir(submod_path):
                    submod_path = os.path.join(submod_path, "__init__.pypp")
                out_lines.append(
                    load_with_imports_renamed(
                        submod_path, loaded, os.path.dirname(submod_path), is_main=False
                    )
                )
            else:
                print(
                    f"[Py++] Error: module '{imp_target}' not found in global or local paths"
                )
                sys.exit(404)

            continue

        # detect funcs
        if mod_name:
            m = re.match(
                r"^(?:(const)\s+)?fn\s+([a-zA-Z0-9_]\w*)\s*\((.*)\)\s+->\s+(.*?)$",
                stripped,
            )
            if m:
                # Group 2 is the function name
                func_names.append(m.group(2))
                # Convert the function definition to include the module prefix
                const, name, args, rettype = m.groups()
                const_prefix = "const " if const else ""
                # Replace the function definition with the prefixed version
                cpp_line = f"{const_prefix}fn {mod_name}_{name}({args}) -> {rettype}"
                out_lines.append(cpp_line)
                continue  # Skip adding the original line

        # detect globals
        if mod_name:
            v = re.match(
                r"^(?:const\s+)?(int|float|double|char|bool|auto|std::string|std::vector<[^>]+>)\s+([a-zA-Z0-9_]\w*)(\s*)?(=.*)?$",
                stripped,
            )
            if v:
                var_names.append(v.group(2))

        out_lines.append(line)

    combined = "\n".join(out_lines)

    if mod_name and (func_names or var_names):
        all_symbols = func_names + var_names
        for name in all_symbols:
            renamed = f"{mod_name}_{name}"
            combined = "\n".join(
                safe_replace(line, name, renamed) for line in combined.splitlines()
            )

        print(f"Imported {mod_name} ({len(func_names)} funcs, {len(var_names)} vars)")

    return combined


# ---------------------------------------------------------------------------
#  Preprocessor: simple defines + single-arg macros
# ---------------------------------------------------------------------------


def preprocess_defines(source: str) -> str:
    # allow multiple args inside parentheses
    define_pattern = re.compile(r"^define\s+([A-Za-z_]\w*)(?:\((.*?)\))?\s+(.+)$")
    defines = {}

    prelude = [
        "define __argcv__ int argc, char** argv",
        "define strvec std::vector<std::string>",
        "define vec std::vector",
    ]

    source_lines: List[str] = prelude + source.splitlines()

    lines = []
    for line in source_lines:
        m = define_pattern.match(line.strip())
        if m:
            name, args_str, value = m.groups()
            if args_str:
                args = [a.strip() for a in args_str.split(",")]
            else:
                args = []
            defines[name] = (args, value)
        else:
            lines.append(line)

    processed = "\n".join(lines)

    # expand macros
    for name, (args, value) in defines.items():
        if args:
            # match name( ... )
            pattern = rf"\b{name}\(([^)]*)\)"

            def repl(m):
                call_args = [a.strip() for a in m.group(1).split(",")]
                result = value
                for arg_name, call_val in zip(args, call_args):
                    # replace arg name with call value
                    result = re.sub(rf"\b{re.escape(arg_name)}\b", call_val, result)
                return f"{result}"

            processed = re.sub(pattern, repl, processed)
        else:
            # plain replacement
            processed = re.sub(rf"\b{name}\b", value, processed)

    return processed


def expand_ranges_outside_strings(src: str) -> str:
    result = ""
    in_str = False
    quote_char = ""
    i = 0
    while i < len(src):
        c = src[i]

        # toggle string mode
        if c in ('"', "'"):
            if not in_str:
                in_str = True
                quote_char = c
            elif src[i - 1] != "\\" and c == quote_char:
                in_str = False
            result += c
            i += 1
            continue

        if not in_str:
            # detect pattern like 3..8:2
            m = re.match(r"([0-9-]+)\s*\.\.\s*([0-9-]+)(?::([0-9-]+))?", src[i:])
            if m:
                a, b = m.group(1), m.group(2)
                c = m.group(3) or 1
                # replace with range-based initializer list
                result += (
                    "{"
                    + ",".join(
                        str(j)
                        for j in range(
                            int(a), int(b) + 1 if int(b) > 0 else int(b) - 1, int(c)
                        )
                    )
                    + "}"
                )
                i += m.end()
                continue

        result += c
        i += 1
    return result


# ---------------------------------------------------------------------------
#  Block and line transpiler
# ---------------------------------------------------------------------------


class BlockFrame:
    def __init__(self, kind: str):
        self.kind = kind


def split_commas(s: str) -> List[str]:
    parts = []
    inside = False
    current = ""
    for c in s:
        if c == "," and not inside:
            parts.append(current.strip())
            current = ""
        else:
            if c in "\"'":
                inside = not inside
            current += c
    if current.strip():
        parts.append(current.strip())
    return parts


# ---------------------------------------------------------------------------
#  MAIN TRANSPILER
# ---------------------------------------------------------------------------


def transpile_paren_blocks_to_cpp(source: str) -> str:
    source = (
        """
fn sstoi(std::string s) -> int
    try
        return std::stoi(s)
    catch ...
        return -1
    end
end
"""
        + source
    )
    lines = expand_ranges_outside_strings(source).splitlines()

    out_lines: List[str] = [
        "#include <iostream>",
        "#include <cstdint>",
        "#include <cstdlib>",
        "#include <limits>",
        "#include <string>",
        "#include <vector>",
        "#include <cstring>",
        """#if __cplusplus >= 201703L
    #include <filesystem>
    namespace fs = std::filesystem;
#else
    #include <experimental/filesystem>
    namespace fs = std::experimental::filesystem;
#endif""",
        "#define __THIS__ fs::path(__argv[0])",
    ]

    block_stack: List[BlockFrame] = [BlockFrame("root")]

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            continue

        # Check if the original line contains a vector comprehension
        vec_comp_pattern = r"((?:std::vector<[^>]+>|std::vector<std::string>)\s+)?(\w+)\s*=\s*\((.+?)\s+foreach\s+(\w+)\s+(.+?)\)"
        vec_match = re.search(vec_comp_pattern, lines[i - 1])
        if vec_match:
            full_type = vec_match.group(
                1
            )  # Full type like std::vector<T> (can be None)
            varname = vec_match.group(2)  # Variable name
            expr = vec_match.group(3)  # Expression to evaluate
            foreach_var = vec_match.group(4)  # Loop variable
            container = vec_match.group(5)  # Container to iterate over

            if full_type:
                out_lines.append(f"{full_type.strip()} {varname} = {{}};")
            else:
                out_lines.append(f"{varname} = {{}};")

            out_lines.append(f"for (auto &{foreach_var} : {container}) {{")
            out_lines.append(f"    {varname}.push_back({expr});")
            out_lines.append("}")
            continue  # Skip the rest of processing for this line

        if "%>" in s:
            s = s.split("%>", 1)[0].strip()
            if not s:
                continue

        if s == "end":
            if len(block_stack) > 1:
                is_cls = block_stack.pop() == "cls"
                out_lines.append("};" if is_cls else "}")
            continue

        m_if = re.match(r"^(if|elif)\s+(.*)$", s)
        m_else = re.match(r"^else$", s)
        m_cls = re.match(r"^cls\s([a-zA-Z0-9_]+)$", s)
        m_repeat = re.match(r"^repeat\s+(.+?)$", s)
        m_while = re.match(r"^while\s+(.*)$", s)
        m_try = re.match(r"^try$", s)
        m_catch = re.match(r"^catch\s+(.*)$", s)
        m_foreach = re.match(r"^foreach\s+(\w+)\s+(.*)$", s)
        m_forever = re.match(r"^forever$", s)
        m_funcdef = re.match(
            r"^(?:(const)\s+)?fn\s+([a-zA-Z0-9_]\w*)?\s*\((.*)\)\s+->\s+(.*?)?$", s
        )

        if m_foreach:
            var, arr = m_foreach.groups()
            if ".." in arr:
                arr = (
                    "{"
                    + ",".join(
                        str(i)
                        for i in range(int(arr.split("..")[0]), int(arr.split("..")[1]))
                    )
                    + "}"
                )
            out_lines.append(f"for (auto &{var} : {arr}) {{")
            block_stack.append(BlockFrame("foreach"))
            continue
        elif m_while:
            cond = m_while.group(1)
            out_lines.append(f"while ({cond}) {{")
            block_stack.append(BlockFrame("while"))
            continue
        elif m_funcdef:
            const, name, args, rettype = m_funcdef.groups()
            # Check if any of the required components are None (not matched)
            if not name or not rettype:
                print(f"[X] Error at line {i}\n{s} <- missing parameters")
                break

            const_prefix = "const " if const else ""
            out_lines.append(f"{const_prefix}{rettype} {name}({args}) {{")
            block_stack.append(BlockFrame("funcdef"))
            continue  # Don't add the original line again
        elif m_if:
            kw, cond = m_if.groups()
            out_lines.append(f"{'if' if kw == 'if' else '} else if'} ({cond}) {{")
            if kw == "elif":
                block_stack.pop()
            block_stack.append(BlockFrame(kw))
            continue
        elif m_else:
            out_lines.append("} else {")
            block_stack.pop()
            block_stack.append(BlockFrame("else"))
            continue
        elif m_try:
            out_lines.append("try {")
            block_stack.append(BlockFrame("try"))
            continue
        elif m_catch:
            exception = m_catch.group(1)
            out_lines.append(f"}} catch ({exception}) {{")
            block_stack.pop()
            block_stack.append(BlockFrame("catch"))
            continue
        elif m_forever:
            out_lines.append("while(1) {")
            block_stack.append(BlockFrame("forever"))
            continue
        elif m_repeat:
            count = m_repeat.group(1)
            out_lines.append(f"for(int _=0; _<{count}; _++) {{")
            block_stack.append(BlockFrame("repeat"))
            continue
        elif m_cls:
            name = m_cls.group(1)
            out_lines.append(f"class {name} {{")
            block_stack.append(BlockFrame("cls"))
            continue

        if s.startswith("print("):
            inside = s[s.find("(") + 1 : s.rfind(")")]
            args = split_commas(inside)
            out_lines.append("std::cout << " + " << ".join(args) + ";")
            continue
    
        if s.startswith("assert:"):
            statement = s[7:].strip()
            tmp = str(uuid.uuid4()).replace("-", "")
            out_lines.append(f"bool ___{tmp} = ({statement});")
            out_lines.append(f"if (!___{tmp}) {{")
            out_lines.append(
                f'std::cout << "Assertion failed:\\n'
                f'    {statement}\\n'
                f'Result: " << ___{tmp} << std::endl;'
            )
            out_lines.append("    std::exit(1);")
            out_lines.append("}")
            continue

        if s.startswith("input(") or s.startswith("numinput("):
            numeric = s.startswith("numinput")
            inside = s[s.find("(") + 1 : s.rfind(")")]
            parts = split_commas(inside)
            if len(parts) >= 2:
                var_name = parts[1]
                prompt = parts[0]
                out_lines.append(f"std::cout << {prompt} << std::flush;")
                if numeric:
                    out_lines.append(f"std::cin >> {var_name};")
                    out_lines.append(
                        "std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\\n');"
                    )
                else:
                    out_lines.append(f"std::getline(std::cin, {var_name});")
            continue

        if not s.endswith((";", "{", "}", ">", ",")) and not s.startswith("#"):
            s += ";"
        out_lines.append(s)
        print_progress(i+1, len(lines)-2)

    while len(block_stack) > 1:
        out_lines.append("}")
        block_stack.pop()

    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py++ <file>")
        sys.exit(1)
        
    if "--setup" in sys.argv:
        i = sys.argv.index("--setup")
        if i + 1 >= len(sys.argv):
            print("Usage: pypp --setup <install_dir>")
            sys.exit(1)
        setup_install(sys.argv[i + 1])
        sys.exit(0)

    if not check_gpp_installed():
        print("please install the g++ compiler")
        sys.exit(1)

    src = preprocess_defines(load_with_imports_renamed(sys.argv[1]))

    # Process vector comprehensions during transpilation by modifying the transpile_paren_blocks_to_cpp function approach
    # Since we already modified the function to handle vector comprehensions, now we just need to call it
    out_cpp = transpile_paren_blocks_to_cpp(src)
    with open("out.cpp", "w", encoding="utf-8") as f:
        f.write(out_cpp)

    if "--dump-asm" not in sys.argv:
        result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-O3",
                "out.cpp",
                "-o",
                f"{sys.argv[1][:-5]}.exe" if os.name == "nt" else sys.argv[1][:-5],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    else:
        result = subprocess.run(
            ["g++", "-S", "-std=c++17", "-O3", "out.cpp", "-o", "out.s"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    if result.returncode != 0:
        print("X Compilation failed:\n")
        print(result.stderr)
        print("out.cpp preserved for debugging")
    else:
        print("V Compilation successful!")
        if "-p" not in sys.argv:
            os.remove("out.cpp")
