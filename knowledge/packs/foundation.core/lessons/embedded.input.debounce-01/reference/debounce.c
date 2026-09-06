#include "debounce.h"

void debounce_init(debounce_t *state, unsigned int initial_state, unsigned int threshold)
{
    state->stable_state = initial_state != 0U;
    state->candidate_state = state->stable_state;
    state->consecutive_count = 0U;
    state->threshold = threshold;
}

unsigned int debounce_update(debounce_t *state, unsigned int sample)
{
    sample = sample != 0U;
    if (sample == state->stable_state) {
        /* 抖回原状态时，此前的新状态采样不再连续。 */
        state->candidate_state = sample;
        state->consecutive_count = 0U;
    } else {
        if (sample != state->candidate_state) {
            state->candidate_state = sample;
            state->consecutive_count = 1U;
        } else if (state->consecutive_count < state->threshold) {
            ++state->consecutive_count;
        }
        if (state->consecutive_count >= state->threshold) {
            state->stable_state = sample;
            state->consecutive_count = 0U;
        }
    }
    return state->stable_state;
}
