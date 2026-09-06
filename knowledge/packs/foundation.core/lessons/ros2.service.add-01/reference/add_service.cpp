#include "add_service.hpp"

AddResponse handle_add(const AddRequest &request)
{
    return {request.a + request.b};
}
