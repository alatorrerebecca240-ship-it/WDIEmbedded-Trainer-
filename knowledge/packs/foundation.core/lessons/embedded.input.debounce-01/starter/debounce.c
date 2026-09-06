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
    /* TODO: 实现连续采样计数和稳定状态切换。 */
    (void)sample;
    return state->stable_state;
}

