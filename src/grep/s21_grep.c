#include "s21_grep.h"

int main(int argc, char **argv) {
  struct options operators = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, REG_EXTENDED};
  int flag = 0, num_pattern_line = 0, num_namefiles = 0, num_reg = 0,
      total_match_count = 0;
  char **pattern_sheet = NULL, **namefiles = NULL;
  regex_t *regex_sheet = NULL;
  if (argc == 1) {
    return 1;
  }
  input(argc, argv, &operators, &pattern_sheet, &num_pattern_line,
        &num_namefiles);

  // добавление шаблона в массив шаблонов
  if (operators.f == 0 && operators.e == 0) {
    pattern_sheet =
        init_line(pattern_sheet, argv[optind], &num_pattern_line, &flag);
    optind++;
  }
  // проверка на ввод имени файла
  if (optind == argc) {
    if (!operators.s) fprintf(stderr, ERROR_01, argv[optind]);
    flag = 1;
  }

  custom_qsort(pattern_sheet, 0, num_pattern_line - 1);

  // добавление имени файла в массив имён файлов
  while (optind < argc) {
    namefiles = init_line(namefiles, argv[optind], &num_namefiles, &flag);
    optind++;
  }

  for (int i = 0; i < num_pattern_line; i++) {
    regex_t regular, *regularP = &regular;
    int is_regular_gen =
        regcomp(regularP, pattern_sheet[i], operators.regex_flag);
    if (is_regular_gen != 0) {
      regfree(regularP);
      if (!operators.s) {
        fprintf(stderr, "!ERROR create regular expression %s\n",
                pattern_sheet[i]);
      }
      flag = 1;
    } else {
      regex_sheet = init_regex_line(regex_sheet, regular, &num_reg, &flag);
    }
  }
  short is_multi_file = 0;
  if (num_namefiles != 1 && !flag) {
    is_multi_file = (short)1;
  }
  for (int i = 0; i < num_namefiles; i++) {
    total_match_count += search(&operators, regex_sheet, num_reg, namefiles[i],
                                is_multi_file, &flag);
  }
  freeng(&namefiles, &num_namefiles, &pattern_sheet, &num_pattern_line,
         &num_reg, &regex_sheet);
  return total_match_count ? 0 : 1;
}

void freeng(char ***namefiles, int *num_namefiles, char ***pattern_sheet,
            int *num_pattern_line, int *num_reg, regex_t **regex_sheet) {
  free_sheet(*namefiles, num_namefiles);
  free_sheet(*pattern_sheet, num_pattern_line);
  for (int i = 0; i < *num_reg; i++) {
    regfree(*regex_sheet + i);
  }
  free(*regex_sheet);
}

int search(struct options *operators, regex_t *regex_sheet, int num_reg,
           char *filename, short is_multi_file, int *flag) {
  size_t count = 0;
  FILE *file = readfile(filename, flag);
  if (file == NULL) {
    if (!operators->s) fprintf(stderr, ERROR_01, filename);
  } else {
    prohod(operators, regex_sheet, num_reg, filename, &count, file,
           is_multi_file);
    if (operators->l) {
      ;
    } else if (operators->c) {
      if (is_multi_file && !operators->h) {
        printf("%s:", filename);
      }
      printf("%ld\n", count);
    }
    fclose(file);
  }
  return count;
}

int prohod(struct options *operators, regex_t *regex_sheet, int num_reg,
           char *filename, size_t *count, FILE *file, short is_multi_file) {
  long unsigned int lenght = 2, count_all_string = 0;
  int reverse = 0, status = 0, check = 0;
  char *tmp_line = NULL;
  if (operators->v == 1) {
    reverse = REG_NOMATCH;
  }
  while (s21_getline(&tmp_line, &lenght, file, 0) != (size_t)-1) {
    count_all_string++;
    int mathch_string_v = 0;
    for (int i = num_reg - 1; i >= 0; i--) {
      regmatch_t regmathp;
      status = regexec(&regex_sheet[i], tmp_line, (size_t)1, &regmathp, 0);
      if (reverse == REG_NOMATCH && status != REG_NOMATCH) {
        mathch_string_v = 1;
      }
      if (status == reverse && !mathch_string_v) {
        (*count)++;
        if (operators->l) {
          printf("%s\n", filename);
          check = 1;
        } else if (operators->c) {
          ;
        } else if (operators->n) {
          if (operators->o) {
            flag_o(&regex_sheet[i], tmp_line, regmathp, count_all_string,
                   operators, is_multi_file, filename);
          } else if (is_multi_file && !operators->h) {
            printf("%s:%ld:%s\n", filename, count_all_string, tmp_line);
          } else {
            printf("%ld:%s\n", count_all_string, tmp_line);
          }
        } else if (operators->o) {
          flag_o(&regex_sheet[i], tmp_line, regmathp, count_all_string,
                 operators, is_multi_file, filename);
        } else {
          (operators->h || !is_multi_file)
              ? printf("%s\n", tmp_line)
              : printf("%s:%s\n", filename, tmp_line);
        }
        break;
      }
    }
    if (check) {
      free(tmp_line);
      break;
    }
  }
  return 0;
}

void flag_o(regex_t *reg, char *tmp_line, regmatch_t regmathp,
            int count_all_string, struct options *operators, int is_multi_file,
            char *filename) {
  int offset = 0;
  regmathp.rm_so = regmathp.rm_so < 0 ? 0 : regmathp.rm_so;
  regmathp.rm_eo = regmathp.rm_eo < 0 ? (size_t)(strlen(tmp_line) - 1)
                                      : (size_t)regmathp.rm_eo;
  char *buffer = malloc((regmathp.rm_eo - regmathp.rm_so + 1) * sizeof(char));

  while (regexec(reg, (tmp_line + offset), (size_t)1, &regmathp, 0) !=
         REG_NOMATCH) {
    int j = 0;
    for (regoff_t i = regmathp.rm_so; i < regmathp.rm_eo; i += sizeof(char)) {
      buffer[j++] = (tmp_line + offset)[i];
    }
    offset += regmathp.rm_eo;
    buffer[j] = '\0';

    if (operators->n && is_multi_file && !operators->h) {
      printf("%s:%d:%s\n", filename, count_all_string, buffer);
    } else if (operators->n) {
      printf("%d:%s\n", count_all_string, buffer);
    } else if (is_multi_file && !operators->h) {
      printf("%s:%s\n", filename, buffer);
    } else {
      printf("%s\n", buffer);
    }
  }
  free(buffer);
}

FILE *readfile(char *filename, int *flag) {
  FILE *file = fopen(filename, "r");
  if (file == NULL) {
    *flag = 1;
  }
  return file;
}

regex_t *init_regex_line(regex_t *sheet, regex_t new_line, int *num_line,
                         int *flag) {
  regex_t *temp = realloc(sheet, (*num_line + 1) * sizeof(regex_t));
  if (temp) {
    sheet = temp;
    sheet[*num_line] = new_line;
  } else {
    *flag = 1;
    regfree(temp);
    temp = NULL;
  }
  *num_line = *num_line + 1;
  return sheet;
}

void input(int argc, char **argv, struct options *operators,
           char ***pattern_sheet, int *num_pattern_line, int *flag) {
  int check = 0;
  while ((check = getopt(argc, argv, "e:ivclnhsof:")) != -1) {
    switch (check) {
      case 'i':
        operators->i = 1;
        operators->regex_flag = REG_EXTENDED | REG_ICASE;
        break;
      case 'v':
        operators->v = 1;
        break;
      case 'c':
        operators->c = 1;
        break;
      case 'l':
        operators->l = 1;
        break;
      case 'n':
        operators->n = 1;
        break;
      case 'h':
        operators->h = 1;
        break;
      case 's':
        operators->s = 1;
        opterr = 0;
        break;
      case 'o':
        operators->o = 1;
        break;
      case 'f':
        operators->f = 1;
        setOptionsF(pattern_sheet, num_pattern_line, optarg, flag);
        break;
      case 'e':
        operators->e = 1;
        setOptionsE(pattern_sheet, num_pattern_line, optarg, flag);
        break;
    }
  }
}

char **init_line(char **sheet, char *new_line, int *num_line, int *flag) {
  int num = *num_line;
  char **temp = realloc(sheet, (num + 1) * sizeof(char *));
  if (temp) {
    sheet = temp;
    sheet[num] = s21_strdup(new_line);
    if (sheet[num] == NULL) {
      *flag = 1;
    } else {
      *num_line = num + 1;
    }
  } else {
    *flag = 1;
    free(temp);
    temp = NULL;
  }
  return sheet;
}
char *s21_strdup(char *new_line) {
  char *result = malloc(sizeof(char *) * (strlen(new_line) + 1));
  if (result) {
    int i = 0;
    for (i = 0; i <= (int)strlen(new_line); i++) {
      result[i] = new_line[i];
    }
  } else {
    free(result);
    result = NULL;
  }
  return result;
}

int free_sheet(char **sheet, int *num_line) {
  for (int i = 0; i < *num_line; i++) {
    free(sheet[i]);
  }
  free(sheet);
  return 0;
}

void setOptionsE(char ***pattern_sheet, int *num_pattern_line, char *optarg,
                 int *flag) {
  *pattern_sheet = init_line(*pattern_sheet, optarg, num_pattern_line, flag);
}

void setOptionsF(char ***pattern_sheet, int *num_pattern_line, char *optarg,
                 int *flag) {
  size_t now = 0;
  size_t lenght = 2;
  char *new_line = NULL;
  FILE *file = readfile(optarg, flag);
  if (file == NULL) {
    fprintf(stderr, ERROR_01, optarg);
    *flag = 1;
    exit(1);
  }
  while (now != (size_t)-1) {
    now = s21_getline(&new_line, &lenght, file, 1);
    if (now != (size_t)-1 && new_line) {
      *pattern_sheet =
          init_line(*pattern_sheet, new_line, num_pattern_line, flag);
    }
  }
  fclose(file);
}

size_t s21_getline(char **lineptr, size_t *n, FILE *stream, int flag_for_f) {
  size_t bufsize = *n, i = 0;
  char *buffer = *lineptr;
  int c = 0;
  char *new_buffer = (char *)realloc(buffer, bufsize + 1);
  if (new_buffer == NULL) {
    free(buffer);
    buffer = NULL;
  }
  buffer = new_buffer;

  while ((c = fgetc(stream)) != EOF && c != '\n') {
    if (bufsize - i <= 0) {
      bufsize += 2;
      char *new_buffer = (char *)realloc(buffer, bufsize + 1);
      if (new_buffer == NULL) {
        free(buffer);
        buffer = NULL;
      }
      buffer = new_buffer;
    }
    buffer[i++] = (char)c;
    if (c == '\n') {
      if (flag_for_f) {
        buffer[i - 1] = '\0';
      }
      break;
    }
  }
  buffer[i] = '\0';
  if (i == 0 && c == EOF) {
    free(buffer);
    buffer = NULL;
    i = -1;  // Ничего не было прочитано
  } else {
    *lineptr = buffer;
    *n = bufsize;
  }
  return i;
}

// Функция для сравнения двух строк
int compareStrings(const void *a, const void *b) {
  const char *str1 = *(const char **)a;
  const char *str2 = *(const char **)b;
  return strcmp(str1, str2);
}

// Функция для обмена двух указателей на строки
void swap(char **a, char **b) {
  char *temp = *a;
  *a = *b;
  *b = temp;
}

// Реализация функции qsort
void custom_qsort(char **arr, int low, int high) {
  if (low < high) {
    int pivot = low;
    int i = low;
    int j = high;

    while (i < j) {
      while (compareStrings(&arr[i], &arr[pivot]) <= 0 && i < high) i++;
      while (compareStrings(&arr[j], &arr[pivot]) > 0 && j > low) j--;
      if (i <= j) swap(&arr[i], &arr[j]);
    }

    swap(&arr[pivot], &arr[j]);
    custom_qsort(arr, low, j - 1);
    custom_qsort(arr, j + 1, high);
  }
}
