#ifndef TRAINER_LIST_COUNT_H
#define TRAINER_LIST_COUNT_H

#include <stddef.h>

typedef struct Node {
    int value;
    struct Node *next;
} Node;

size_t list_count(const Node *head);

#endif
