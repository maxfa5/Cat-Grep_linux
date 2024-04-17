#ifndef S21_CAT_H_
#define S21_CAT_H_

#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define STR_MAX_SIZE 10000

struct options {
  int e;
  int v;
  int n;
  int s;
  int b;
  int t;
  int T;
  int E;
};

void cat(FILE *f, struct options *options, int *count_str, int *count_str_b,
         int is_next);
void vetT(char *str, struct options *options);
void flag_s(int *isPreviousStringEmpty, char *soderj, struct options *options,
            int *j, int *flag);
void T_print(unsigned char c);
void v_print(unsigned char c);
long int filesize(FILE *fp);
void input(int argc, char **argv, struct options *options);
#endif