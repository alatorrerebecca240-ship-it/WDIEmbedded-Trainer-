#ifndef TRAINER_DEBOUNCE_H
#define TRAINER_DEBOUNCE_H

typedef struct {
    unsigned int stable_state;
    unsigned int candidate_state;
    unsigned int consecutive_count;
    unsigned int threshold;
} debounce_t;

void debounce_init(debounce_t *state, unsigned int initial_state, unsigned int threshold);
unsigned int debounce_update(debounce_t *state, unsigned int sample);

#endif
