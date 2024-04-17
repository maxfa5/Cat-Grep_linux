all: s21_cat

s21_cat : 
	gcc -Wall -Wextra -std=c11 s21_cat.c s21_cat.h -o s21_cat

clean:
	rm -rf s21_cat

test1:
	bash tests.sh

test2:
	python3 tests.py

clang:
	clang-format -n *.c