all: s21_grep 

s21_grep:
	gcc -Wall -Wextra -std=c11 s21_grep.c s21_grep.h -o s21_grep

clean:
	rm -rf s21_grep

test1:
	bash tests.sh

test2:
	python3 tests.py
	
clang:
	clang-format -n *.c