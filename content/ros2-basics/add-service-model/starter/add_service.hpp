#ifndef TRAINER_ADD_SERVICE_HPP
#define TRAINER_ADD_SERVICE_HPP
#include <cstdint>
struct AddRequest { std::int64_t a; std::int64_t b; };
struct AddResponse { std::int64_t sum; };
AddResponse handle_add(const AddRequest &request);
#endif
