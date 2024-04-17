#ifndef S21_GREP_H_
#define S21_GREP_H_

#include <getopt.h>
#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ERROR_01 "s21_grep: %s: No such file or directory\n"

struct options {
  int e;
  int i;
  int v;
  int c;
  int l;
  int n;
  int h;
  int s;
  int f;
  int o;
  int regex_flag;
};

char *readstr(char *buffer, FILE *file, int numberStr);
regex_t *check_expression(regex_t *reg, char *pattern, int reg_flag, int *flag);
regex_t *init_regex_line(regex_t *sheet, regex_t new_line, int *num_line,
                         int *flag);
char **init_line(char **sheet, char *new_line, int *num_line, int *flag);
int free_sheet(char **sheet, int *num_line);
int prohod(struct options *operators, regex_t *regex_sheet, int num_reg,
           char *filename, size_t *count, FILE *file, short is_multi_file);
FILE *readfile(char *filename, int *flag);
void flag_o(regex_t *reg, char *tmp_line, regmatch_t regmathp,
            int count_all_string, struct options *operators, int is_multi_file,
            char *filename);
char *s21_strdup(char *new_line);
size_t s21_getline(char **lineptr, size_t *n, FILE *stream, int flag_for_f);
void swap(char **a, char **b);
int compareStrings(const void *a, const void *b);
void custom_qsort(char **arr, int low, int high);
int search(struct options *operators, regex_t *regex_sheet, int num_reg,
           char *filename, short is_multi_file, int *flag);
void input(int argc, char **argv, struct options *operators,
           char ***pattern_sheet, int *num_pattern_line, int *flag);
void setOptionsE(char ***pattern_sheet, int *num_pattern_line, char *optarg,
                 int *flag);
void setOptionsF(char ***pattern_sheet, int *num_pattern_line, char *optarg,
                 int *flag);
void freeng(char ***namefiles, int *num_namefiles, char ***pattern_sheet,
            int *num_pattern_line, int *num_reg, regex_t **regex_sheet);
#endif