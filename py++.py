import os, re, sys, subprocess, shutil
from typing import List, Dict, Set, Optional

def add_to_path_win(target_dir: str):
    subprocess.run([
        "powershell", "-Command",
        f'[Environment]::SetEnvironmentVariable("Path", $env:Path + ";{target_dir}", "User")'
    ], shell=True)

def setup_install(target_dir: str):
    os.makedirs(os.path.join(target_dir, "modules"), exist_ok=True)

    builtins = {
        "modules/fileOps.pypp": '''
#include <fstream>
#include <vector>

std::string read_file(const std::string &path) {
    std::ifstream f(path);
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}

void write_file(const std::string &path, const std::string &content) {
    std::ofstream f(path);
    f << content;
}

std::vector<std::string> read_lines(const std::string &path) {
    std::ifstream f(path);
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(f, line)) lines.push_back(line);
    return lines;
}

void appnd_to_file(const std::string &path, const std::string &content) {
    std::ofstream f(path, std::ios::app); 
    f << content;
}
''',
        "modules/std/time.pypp": '''
#include <chrono>
#include <thread>
#include <ctime>
#include <sstream>
#include <iomanip>

double now_() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count()
}

void sleep(double seconds) {
    std::this_thread::sleep_for(std::chrono::duration<double>(seconds));
}

double since(double start) {
    return now_() - start
}

std::string format(const std::string& fmt) {
    std::time_t t = std::time(nullptr);
    std::tm tm = *std::localtime(&t);
    std::ostringstream oss;
    oss << std::put_time(&tm, fmt.c_str());
    return oss.str()
}

void wait_until(double target) {
    double diff = target - now_();
    if (diff > 0) sleep(diff);
}
''',
        "modules/std/__init__.pypp": '''
imp time
imp random
''', 
        "modules/std/random.pypp": '''
#include <cmath>
imp time


double rand01() {
    double __seed = fmod(time_now_() * 6364136223846793005.0 + 1.0, 1e9)
    return fmod(__seed / 1e9, 1.0)
}

int randint(int a, int b) {
    return a + (int)(rand01() * (b - a + 1))
}

double uniform(double a, double b) {
    return a + rand01() * (b - a)
}

int randlen(int length) {
    if (length <= 0) return 0;
    int num = randint(1, 9); 
    for (int i = 1; i < length; i++) {
        int digit = randint(0, 9);
        num = num * 10 + digit;
    }
    return num
}
''', 
        "modules/std/sys.pypp": '''
#include <string>

#ifdef _WIN32
#include <windows.h>
#include <locale>
#include <codecvt>
#endif

std::string get_username() {
#ifdef _WIN32
    wchar_t buffer[256];
    DWORD size = 256;
    if (GetUserNameW(buffer, &size)) {
        std::wstring_convert<std::codecvt_utf8<wchar_t>> conv;
        return conv.to_bytes(buffer);
    } else {
        return "???"
    }
#else
    const char* user = std::getenv("USER");
    return user ? std::string(user) : "???"
#endif
}
'''
    }

    # Write built-in modules
    for rel, content in builtins.items():
        path = os.path.join(target_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # Detect mode (exe or script)
    if getattr(sys, 'frozen', False):
        self_path = sys.executable
    else:
        self_path = os.path.abspath(sys.argv[0])

    dest = os.path.join(target_dir, os.path.basename(self_path))
    if os.path.abspath(self_path) != os.path.abspath(dest):
        try:
            shutil.copy2(self_path, dest)
            print(f"📦 Copied installer to {dest}")
        except Exception as e:
            print(f"⚠️ Could not copy self: {e}")

    # Add to PATH only if not already there
    path_env = os.environ.get("PATH", "")
    paths = [p.strip() for p in path_env.split(os.pathsep)]
    if target_dir not in paths:
        if os.name == "nt":
            add_to_path_win(target_dir)
        else:
            bashrc = os.path.expanduser("~/.bashrc")
            with open(bashrc, "a", encoding="utf-8") as f:
                f.write(f'\nexport PATH="$PATH:{target_dir}"\n')
        print(f"✨ Added {target_dir} to PATH")
    else:
        print(f"🫶 {target_dir} already in PATH, skipping")

    print(f"\n✅ Py++ installed to: {target_dir}")
    print("💡 Restart your terminal to use the 'py++' command globally!\n")

def check_gpp_installed() -> bool:
    try:
        result = subprocess.run(
            ["g++", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
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
        if c == '"' and (i == 0 or line[i-1] != '\\'):
            in_str = not in_str
            new_line += c
            i += 1
            continue
        if in_str:
            new_line += c
            i += 1
            continue

        # try to match the function name as a standalone token
        if line[i:i+len(name)] == name:
            before = line[i-1] if i > 0 else " "
            after = line[i+len(name)] if i+len(name) < len(line) else " "
            if not before.isalnum() and before != '_' and not after.isalnum() and after != '_':
                new_line += replacement
                i += len(name)
                continue

        new_line += c
        i += 1
    return new_line

def load_with_imports_renamed(path: str, loaded: Optional[Set[str]] = None, base_dir: Optional[str] = None, is_main: bool = True) -> str:
    if loaded is None:
        loaded = set()

    if base_dir is None:
        base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

    norm_path = os.path.abspath(path)
    if norm_path in loaded:
        return ""
    loaded.add(norm_path)

    if not os.path.exists(path):
        print(f"[Py++] Warning: file '{path}' not found")
        return ""

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

        # handle imports
        if stripped.startswith("imp "):
            imp_target = stripped[4:].strip()
            if "/" not in imp_target and os.path.isdir(os.path.join(base_dir, imp_target)):
                submod_path = os.path.join(base_dir, imp_target, "__init__.pypp")
            else:
                submod_path = os.path.join(base_dir, imp_target + ".pypp")
                if not os.path.exists(submod_path):
                    submod_path = os.path.join(base_dir, "modules", imp_target + ".pypp")

            if os.path.exists(submod_path):
                out_lines.append(load_with_imports_renamed(submod_path, loaded, os.path.dirname(submod_path), is_main=False))
            else:
                out_lines.append(f"// [Py++] Warning: module '{imp_target}' not found")
            continue

        # detect functions
        if mod_name:
            m = re.match(
                r'^(?:const\s+)?(int|float|double|char|bool|void|auto|std::string|std::vector<[^>]+>)\s+([a-zA-Z_]\w*)\s*\(.*\)\s*\{?$',
                stripped
            )
            if m:
                func_names.append(m.group(2))

        # detect global variables
        if mod_name:
            v = re.match(
                r'^(?:const\s+)?(int|float|double|char|bool|auto|std::string|std::vector<[^>]+>)\s+([a-zA-Z0-9_]\w*)(\s*)?(=.*)?$',
                stripped
            )
            if v:
                var_names.append(v.group(2))

        out_lines.append(line)

    combined = "\n".join(out_lines)

    # rename both functions and vars
    if mod_name and (func_names or var_names):
        all_symbols = func_names + var_names
        for name in all_symbols:
            renamed = f"{mod_name}_{name}"
            combined = "\n".join(safe_replace(l, name, renamed) for l in combined.splitlines())

        print(f"Imported {mod_name} ({len(func_names)} funcs, {len(var_names)} vars)")

    return combined

# ---------------------------------------------------------------------------
#  Preprocessor: simple defines + single-arg macros
# ---------------------------------------------------------------------------

def preprocess_defines(source: str) -> str:
    # allow multiple args inside parentheses
    define_pattern = re.compile(r"^define\s+([A-Za-z_]\w*)(?:\((.*?)\))?\s+(.+)$")
    defines = {}

    lines = []
    for line in source.splitlines():
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
            if c in "\"'": inside = not inside
            current += c
    if current.strip():
        parts.append(current.strip())
    return parts

# ---------------------------------------------------------------------------
#  MAIN TRANSPILER
# ---------------------------------------------------------------------------

def transpile_paren_blocks_to_cpp(source: str) -> str:
    lines = source.splitlines()
    out_lines: List[str] = [
        '#include <iostream>',
        '#include <cstdint>',
        '#include <cstdlib>', 
        '#include <limits>',
        '#include <string>',
        '''#if __cplusplus >= 201703L
    #include <filesystem>
    namespace fs = std::filesystem;
#else
    #include <experimental/filesystem>
    namespace fs = std::experimental::filesystem;
#endif''',
        '#define __THIS__ fs::path(__argv[0])',
        'const double factorial_table[171] = {1.0,1.0,2.0,6.0,24.0,120.0,720.0,5040.0,40320.0,362880.0,3628800.0,39916800.0,479001600.0,6227020800.0,87178291200.0,1307674368000.0,20922789888000.0,355687428096000.0,6402373705728000.0,1.21645100408832e+17,2.43290200817664e+18,5.109094217170944e+19,1.1240007277776077e+21,2.585201673888498e+22,6.204484017332394e+23,1.5511210043330986e+25,4.0329146112660565e+26,1.0888869450418352e+28,3.0488834461171384e+29,8.841761993739701e+30,2.6525285981219103e+32,8.222838654177922e+33,2.631308369336935e+35,8.683317618811886e+36,2.9523279903960412e+38,1.0333147966386144e+40,3.719933267899012e+41,1.3763753091226343e+43,5.23022617466601e+44,2.0397882081197442e+46,8.159152832478977e+47,3.3452526613163803e+49,1.4050061177528798e+51,6.041526306337383e+52,2.6582715747884485e+54,1.1962222086548019e+56,5.5026221598120885e+57,2.5862324151116818e+59,1.2413915592536073e+61,6.082818640342675e+62,3.0414093201713376e+64,1.5511187532873822e+66,8.065817517094388e+67,4.2748832840600255e+69,2.308436973392414e+71,1.2696403353658276e+73,7.109985878048635e+74,4.052691950487722e+76,2.350561331282879e+78,1.3868311854568986e+80,8.320987112741392e+81,5.075802138772248e+83,3.146997326038794e+85,1.98260831540444e+87,1.2688693218588417e+89,8.247650592082472e+90,5.443449390774431e+92,3.647111091818868e+94,2.4800355424368305e+96,1.711224524281413e+98,1.197857166996989e+100,8.504785885678622e+101,6.123445837688608e+103,4.4701154615126834e+105,3.3078854415193856e+107,2.480914081139539e+109,1.8854947016660498e+111,1.4518309202828584e+113,1.1324281178206295e+115,8.946182130782973e+116,7.156945704626378e+118,5.797126020747366e+120,4.75364333701284e+122,3.945523969720657e+124,3.314240134565352e+126,2.8171041143805494e+128,2.4227095383672724e+130,2.107757298379527e+132,1.8548264225739836e+134,1.6507955160908452e+136,1.4857159644817607e+138,1.3520015276784023e+140,1.24384140546413e+142,1.1567725070816409e+144,1.0873661566567424e+146,1.0329978488239052e+148,9.916779348709491e+149,9.619275968248206e+151,9.426890448883242e+153,9.33262154439441e+155,9.33262154439441e+157,9.425947759838354e+159,9.614466715035121e+161,9.902900716486175e+163,1.0299016745145622e+166,1.0813967582402903e+168,1.1462805637347078e+170,1.2265202031961373e+172,1.3246418194518284e+174,1.4438595832024928e+176,1.5882455415227421e+178,1.7629525510902437e+180,1.9745068572210728e+182,2.2311927486598123e+184,2.543559733472186e+186,2.925093693493014e+188,3.3931086844518965e+190,3.969937160808719e+192,4.6845258497542883e+194,5.574585761207603e+196,6.689502913449124e+198,8.09429852527344e+200,9.875044200833598e+202,1.2146304367025325e+205,1.5061417415111404e+207,1.8826771768889254e+209,2.372173242880046e+211,3.012660018457658e+213,3.8562048236258025e+215,4.9745042224772855e+217,6.466855489220472e+219,8.471580690878817e+221,1.118248651196004e+224,1.4872707060906852e+226,1.992942746161518e+228,2.6904727073180495e+230,3.659042881952547e+232,5.01288874827499e+234,6.917786472619486e+236,9.615723196941086e+238,1.346201247571752e+241,1.89814375907617e+243,2.6953641378881614e+245,3.8543707171800706e+247,5.550293832739301e+249,8.047926057471987e+251,1.17499720439091e+254,1.7272458904546376e+256,2.5563239178728637e+258,3.808922637630567e+260,5.7133839564458505e+262,8.627209774233235e+264,1.3113358856834518e+267,2.006343905095681e+269,3.089769613847349e+271,4.789142901463391e+273,7.47106292628289e+275,1.1729568794264138e+278,1.8532718694937338e+280,2.946702272495037e+282,4.714723635992059e+284,7.590705053947215e+286,1.2296942187394488e+289,2.0044015765453015e+291,3.2872185855342945e+293,5.423910666131586e+295,9.003691705778433e+297,1.5036165148649983e+300,2.526075744973197e+302,4.2690680090047027e+304,7.257415615307994e+306};',
        'double factorial(int n){if (n <= 171) return factorial_table[n];return 1e308;}'
    ]

    vartypes: Dict[str, str] = {}
    block_stack: List[BlockFrame] = [BlockFrame('root')]

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            continue

        if "%>" in s:
            s = s.split("%>", 1)[0].strip()
            if not s:
                continue

        if s == ")":
            if len(block_stack) > 1:
                is_cls = block_stack.pop() == "cls"
                out_lines.append("};" if is_cls else "}")
            continue

        m_if = re.match(r'^(if|elif)\s+(.*)\s*\($', s)
        m_else = re.match(r'^else\s*\($', s)
        m_cls = re.match(r'^cls\s([a-zA-Z0-9_]+)\s*\($', s)
        m_repeat = re.match(r'^repeat\s+(.+?)\s*\($', s)
        m_foreach = re.match(r'^foreach\s+(\w+)\s+(.*)\s*\($', s)
        m_forever = re.match(r'^forever\s*\($', s)
        m_return = re.match(r'^return\s+([a-zA-Z0-9_]+\s*(,\s*[a-zA-Z0-9_]+)*)\s*;', s)

        if m_foreach:
            var, arr = m_foreach.groups()
            if ".." in arr:
                arr = "{" + ",".join(str(i) for i in range(int(arr.split("..")[0]), int(arr.split("..")[1]))) + "}"
            out_lines.append(f'for (auto &{var} : {arr}) {{')
            block_stack.append(BlockFrame("foreach"))
            continue
        elif m_return:
            varsa = m_return.groups(1)
            out_lines.append(f'return std::make_tuple({varsa});')
            continue
        elif m_if:
            kw, cond = m_if.groups()
            out_lines.append(f"{'if' if kw=='if' else 'else if'} ({cond}) {{")
            block_stack.append(BlockFrame(kw))
            continue
        elif m_else:
            out_lines.append("else {")
            block_stack.append(BlockFrame("else"))
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

        if s.startswith("print"):
            inside = s[s.find("(")+1:s.rfind(")")]
            args = split_commas(inside)
            out_lines.append("std::cout << " + " << ".join(args) + ";")
            continue

        if s.startswith("input") or s.startswith("numinput"):
            numeric = s.startswith("numinput")
            inside = s[s.find("(")+1:s.rfind(")")]
            parts = split_commas(inside)
            if len(parts) >= 2:
                var_name = parts[1]
                prompt = parts[0]
                out_lines.append(f'std::cout << {prompt} << std::flush;')
                if numeric:
                    out_lines.append(f'std::cin >> {var_name};')
                    out_lines.append('std::cin.ignore(std::numeric_limits<std::streamsize>::max(), \'\\n\');')
                else:
                    out_lines.append(f'std::getline(std::cin, {var_name});')
            continue

        if not s.endswith((';', '{', '}', '>')) and not s.startswith('#'):
            s += ";"
        out_lines.append(s)

    while len(block_stack) > 1:
        out_lines.append("}")
        block_stack.pop()

    return "\n".join(out_lines)

# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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
    out_cpp = transpile_paren_blocks_to_cpp(src)
    with open("out.cpp", "w", encoding="utf-8") as f:
        f.write(out_cpp)

    if not "--dump-asm" in sys.argv:
        result = subprocess.run(
            ["g++", "-std=c++17", "-O3", "out.cpp", "-o", f"{sys.argv[1][:-5]}.exe" if os.name == "nt" else sys.argv[1][:-5]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        result = subprocess.run(
            ["g++", "-S", "-std=c++17", "-O3", "out.cpp", "-o", "out.s"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    os.remove("out.cpp")
    if result.returncode != 0:
        print("❌ Compilation failed:\n")
        print(result.stderr)
    else:
        print("✅ Compilation successful!")
