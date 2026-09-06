#include "list_count.h"

size_t list_count(const Node *head)
{
    size_t count = 0U;
    for (const Node *node = head; node; node = node->next) {
        ++count;
    }
    return count;
}
