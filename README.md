# Py++

**Py++** is a Python-inspired transpiler that compiles to **C++**, combining Python’s readability with C++’s speed and low-level power. Py++ source files use the `.pypp` extension.  

---

## Requirements

- **g++** compiler  

---

## Features

- **Pythonic readability:** Block-based structure using indentation and `end` to close blocks, `imp` for imports, and simple variable declarations.  
- **Direct C++ integration:** Mix C++ code with Py++ for performance and system access.  
- **Modular code:** `imp modulename` imports modules or your own code.  
- **Macros & defines:** Flexible metaprogramming using `define` and other macros.  
- **Built-in modules:**
    - `std/time` — timing utilities, sleep, formatted time  
    - `std/sys` — system interaction (e.g., username)  
    - `std/random` — random number generation (seeded from clock)  
    - `std/fileOps` — file reading/writing helpers
    - `std/strOps` — string operations like upper/lower

---

## Example: Guess the Number

```cpp
imp std/random
imp std/time
imp std/sys

fn main() -> int
	SetConsoleOutputCP(CP_UTF8)

	print("DISCLAIMER: this game is not recommended for very very VERY sensitive people. If you play, you do so at your own risk!\n\n")

	int guess
	int len
	numinput("Enter the length of random numbers: ", len)

	forever 
	    numinput("Guess a " + std::to_string(len) + "-digit number: ", guess)
	    int num = random_randlen(len)

	    if guess == num
			print("wooo, you guessed correctly!\n")
			time_sleep(1)
		else
			print("booo, you loser ew—you couldn’t look a few seconds into the future and see that the number was ", num, "? ", sys_get_username(), ", you are a failure...\n")
			time_sleep(1)
		end
	end
end
````

---

## Example: Password Generator

```cpp
imp std/random
imp std/strOps
imp std/fileOps
imp std/time

define random_letter letters[random_randint(0, letters.length() - 1)]


std::string letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


fn generate_pwds(int length, int amount) -> strvec
	strvec pwds = {};

	repeat amount 
		std::string pwd = ""

		repeat length 
		    pwd += random_letter
		end

		pwds.push_back(pwd)
	end

	return pwds
end


fn main() -> int
	int length
	int amount
	std::string add_chars

	numinput("password length: ", length)
	numinput("amount: ", amount)
	input("add special characters (blank to skip): ", add_chars)

	letters += add_chars

	double start = time_now_()
	strvec pwds = generate_pwds(length, amount)
	double time_taken = time_since(start)
	
	print("\nTook: ", time_taken, "s\n")

	foreach pwd pwds
		print(pwd, "\n")
	end

	std::string save
	input("Save? Y/n: ", save)

	if strOps_lower(save) == "y"
        foreach pwd pwds
			fileOps_appnd_to_file("passwords.txt", pwd+"\n")
		end
		print("done!")
	end
end
```

---

## Language Overview

* **Variables:**

  ```cpp
  int x
  double y = 3.14
  strvec names = {}
  vec<int> numbers = 0..10
  ```
* **Blocks:** Open a block with indentation, close with `end`.
* **Control Flow:**

  ```cpp
  if cond
      ...
  end

  else
      ...
  end

  repeat N
      ...
  end

  forever
      ...
  end

  foreach item array
      ...
  end

  fn function_name(...) -> return_type
      ...
  end
  ```
* **Input/Output:**

  * `print(...)` — output text
  * `input(prompt, var)` — read string
  * `numinput(prompt, var)` — read number
* **Functions:** `fn function_name(...) -> return_type`, close with `end`
* **Built-in macros:**
  `__argcv__` expands to `int argc, char** argv`

---

## Getting Started

1. **Install the transpiler:**

   ```bash
   py++(.exe on Windows) --setup <install path>
   ```

   Make sure the path is added to your `PATH`.

2. **Write your code:** Save `.pypp` files, import modules, or use C++ directly.

3. **Compile:**

   ```bash
   py++ yourfile.pypp
   ```

   Produces a native binary (e.g., `yourfile.exe` on Windows).

4. **Run your program:**

   ```bash
   ./yourfile  # or yourfile.exe
   ```

---

## Motivation

Py++ is for anyone who wants:

* Python-style readability
* C++ performance
* Easy reuse of C++ libraries or low-level system access

---

## FAQ

* **Can I use C++ code directly?**
  Yes, full C++ syntax is supported.

* **Can I import Python libraries?**
  No, `imp` imports Py++ or C++ modules only.

* **Can I use standard C++ includes?**
  Yes, just use `#include <...>` at the top.

* **Is Py++ a Python transpiler?**
  No, it’s a new language inspired by Python, targeting C++.

---

## License

MIT License

---

> ⚡ Py++ — Pythonic syntax, C++ speed!
