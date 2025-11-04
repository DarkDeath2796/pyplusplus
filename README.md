# Py++

Py++ is a Python-inspired transpiler language that compiles to C++ for fast execution and easy integration with C++ libraries. It combines the concise, beginner-friendly syntax of Python with the power and performance of C++. Py++ source files typically use the `.pypp` extension.

---

## Requires g++

---

## Features

- **Python-like readability:** Block-based structure using indentation and parentheses, `imp` for imports, and easy variable declarations.
- **Direct C++ integration:** You can mix C++ code and standard library usage for advanced performance and access to system features.
- **Easy modularity:** `imp modulename` syntax for importing your own code or provided modules.
- **Macros and defines:** Simple define and macro expansion supports flexible metaprogramming.
- **Useful built-in modules:**
    - `std/time`: Timing utilities, sleep, formatted time.
    - `std/sys`: System interaction (like username detection).
    - `std/random`: Random number generation (seeded from clock).
    - `fileOps`: File reading/writing helpers.

---

## Example: Guess the Number Game

A number guessing game using Py++

```cpp
#include <windows.h>
imp std/random
imp std/time
imp std/sys

int main() {
	SetConsoleOutputCP(CP_UTF8);

	print("DISCLAIMER: this game is not recommended for very very VERY sensitive people. If you play, you do so at your own risk!\n\n")

	int guess
	int len
	numinput("Enter the length of random numbers: ", len)
	forever (
	    numinput("Guess a " << len << " digits long number: ", guess)
	    int num = random_randlen(len)

	    if guess == num (
			print("wooo, you guessed correctly!\n")
			time_sleep(1)
		)
		else (
			print("booo, you looser ew, you couldnt look a couple of seconds into the future and see that the number was ", num, "? ", sys_get_username(), ", you are a failure...\n")
			time_sleep(1)
		)
	)
}
```

---

## Another example: Password generator 

A simple password generator

```cpp
imp std/random


const std::string letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


%> function to get a random letter/number
char get_random_letter() {
	return letters[random_randint(0, letters.length() - 1)]
}

std::string generate_pwd(int length) {
	std::string pwd = ""

	repeat length (
	    pwd += get_random_letter()
	)
	return pwd
}


int main() {
	int length

	numinput("password length: ", length)

	print(generate_pwd(length))
}
```

---

## Language Overview

- **Variables:** `int x`, `double y = 3.14`, like C++
- **Blocks:** Use parenthesis `(` and close with `)` instead of colons and indentation.
- **Control Flow:**
    - `if cond ( ... )`
    - `else ( ... )`
    - `elif cond ( ... )`
    - `repeat N ( ... )` — repeat N times
    - `forever ( ... )` — infinite loop
    - `foreach item array ( ... )` — iterate over iterable
- **IO:**  
    - `print(...)` for output  
    - `input(prompt, var)` reads a line  
    - `numinput(prompt, var)` reads a number  
- **Functions:** Standard C++-style function signatures, but you can use Pythonic simplicity.

---

## Getting Started

1. **Install the transpiler:**
    ```
    py++(.exe on Windows) --setup <install path>
    ```
    Add the install path to your `PATH` if not already.

2. **Write your code:**  
    Save your `.pypp` files. You can import modules or use C++ directly.

3. **Compile to native code:**
    ```
    py++ yourfile.pypp
    ```
    Outputs a compiled native binary (e.g. `yourfile.exe` on Windows).

4. **Run your program:**
    ```
    ./yourfile    # or yourfile.exe on Windows
    ```

---

## Motivation

Py++ is designed for people who like:
- Python-style syntax and simplicity
- Access to C++ performance
- Easy C++ code reuse or low-level systems tasks

---

## FAQ

- **Can I use C++ code directly?**  
  Yes! You can use any C++ inside your `.pypp` just as in a C++ file.

- **Can I import Python libraries?**  
  No, `imp` refers to Py++ or C++ modules.

- **Can I use standard C++ includes?**  
  Yes, just use `#include <...>` at the top of your file.

- **Is this a Python transpiler?**  
  No, it's a new language inspired by Python, targeting C++ as a backend.

---

## License

MIT License

---

> ⚡ Py++: Pythonic syntax, C++ speed!
