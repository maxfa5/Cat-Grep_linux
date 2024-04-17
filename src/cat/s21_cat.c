#include "s21_cat.h"
int main(int argc, char *argv[]) {
  struct options options = {0};
  int count_files = 0, count_str_n = 1, count_str_b = 1, is_next = 0;
  if (argc == 1) {
    printf("n/a");
    return 0;
  }
  input(argc, argv, &options);
  int proper = 0;
  for (int i = 1; i < argc; i++) {
    if (argv[i][0] != '-') {
      proper = i;
      FILE *f;
      f = fopen(argv[proper], "r");
      if (NULL == f) {
        continue;
      } else {
        if (++count_files > 1) {
          if (options.e) printf("$");
          printf("\n");
          is_next = 1;
        };
        cat(f, &options, &count_str_n, &count_str_b, is_next);
        fclose(f);
      }
    }
  }
  return 0;
}

void input(int argc, char **argv, struct options *options) {
  for (int i = 1; i < argc; i++) {
    if (argv[i][0] == '-') {
      int j = 1;
      while (argv[i][j]) {
        int k = j;
        if (argv[i][j] == 'b') {
          options->b = 1;
          j++;
        }
        if ((argv[i][j] == 'n')) {
          options->n = 1;
          j++;
        }
        if (argv[i][j] == 's') {
          options->s = 1;
          j++;
        }
        if (argv[i][j] == 'e') {
          options->e = 1;
          options->v = 1;
          j++;
        }
        if (argv[i][j] == 'E') {
          options->e = 1;
          j++;
        }
        if (argv[i][j] == 't') {
          options->t = 1;
          options->v = 1;
          j++;
        }
        if (argv[i][j] == 'T') {
          options->t = 1;
          j++;
        }
        if (argv[i][j] == 'v') {
          options->v = 1;
          j++;
        }
        if (strcmp(argv[i], "--number-nonblank") == 0) {
          options->b = 1;
          i++;
          break;
        }
        if (strcmp(argv[i], "--squeeze-blank") == 0) {
          options->s = 1;
          i++;
          break;
        }
        if (strcmp(argv[i], "--number") == 0) {
          options->n = 1;
          i++;
          break;
        }
        if (k == j) {
          j++;
        }
      }
    }
  }
}

void cat(FILE *f, struct options *options, int *count_str, int *count_str_b,
         int is_next) {
  char str[STR_MAX_SIZE] = {'0'};
  int isPreviousStringEmpty = 0, flag = 0;

  while (fgets(str, STR_MAX_SIZE, f)) {
    if (is_next && strlen(str) == 1) {
      is_next = 0;
      continue;
    }
    flag = 0;
    if (options->b) {
      if (str[0] != '\n') printf("%6d\t", (*count_str_b)++);
    }
    if (options->n && !options->b && !options->s) {
      printf("%6d\t", (*count_str)++);
    }
    if (options->s) {
      flag_s(&isPreviousStringEmpty, str, options, count_str, &flag);
    }
    if (((options->v || options->e || options->t || options->T) && options->s &&
         (flag)) ||
        ((options->v || options->e || options->t || options->T) &&
         !options->s)) {
      vetT(str, options);
      flag = 0;
    }
    if (((flag) && !(options->v || options->e || options->t || options->T)) ||
        !(options->s || options->v || options->e || options->t || options->T)) {
      printf("%s", str);
    }
  }
}

void flag_s(int *isPreviousStringEmpty, char *soderj, struct options *options,
            int *count_str, int *flag) {
  if (strlen(soderj) == 1) {
    if (*isPreviousStringEmpty == 1) {
      return;
    }
    *isPreviousStringEmpty = 1;
    if (options->n && !options->b) {
      printf("%6d\t", (*count_str)++);
    }
    if (soderj[0] == '\n') {
      if (options->e) printf("$");
      printf("%c", '\n');
      return;
    } else {
      if (options->e) printf("$");
    }
  } else {
    if (options->n && !options->b) {
      printf("%6d\t", (*count_str)++);
    }
    *flag = 1;
  }
  *isPreviousStringEmpty = 0;
}

void vetT(char *str, struct options *options) {
  int symbol, is_print = 0;
  for (int i = 0; i < (int)strlen(str); i++) {
    symbol = str[i];
    is_print = 0;
    if (symbol == '\t' && (options->t)) {
      printf("^I");
      is_print = 1;
    }
    if (symbol == '\n' && is_print == 0 && options->e) {
      printf("$\n");
      is_print = 1;
    }
    if ((symbol == '\n' || symbol == '\t') && !is_print) {
      printf("%c", symbol);
      is_print = 1;
    }

    if (!is_print && options->v) {
      v_print(symbol);
      is_print = 1;
    }
    if (!is_print) {
      printf("%c", symbol);
    }
  }
}

void v_print(unsigned char c) {
  if (c >= 32 && c < 127) {
    printf("%c", c);
  } else if (c == 127) {
    printf("^?");
  } else if (c >= 128 + 32) {
    printf("M-");
    (c < 128 + 127) ? printf("%c", c - 128) : printf("^?");
  } else {
    (c > 32) ? printf("M-^%c", c - 128 + 64) : printf("^%c", c + 64);
  }
}
