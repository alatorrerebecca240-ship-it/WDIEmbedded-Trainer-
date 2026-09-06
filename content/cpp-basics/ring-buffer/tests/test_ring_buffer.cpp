#include "ring_buffer.hpp"

#include <iostream>
#include <string>

static int failures = 0;

static void expect(bool condition, const std::string &message)
{
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        ++failures;
    }
}

int main()
{
    RingBuffer<int, 3> buffer;
    expect(buffer.empty(), "new buffer is empty");
    expect(buffer.push(10), "push first item");
    expect(buffer.push(20), "push second item");
    expect(buffer.size() == 2, "size after two pushes");

    const auto first = buffer.pop();
    expect(first && *first == 10, "FIFO first item");
    expect(buffer.push(30), "push before wrap");
    expect(buffer.push(40), "push after wrap");
    expect(buffer.full(), "buffer is full");
    expect(!buffer.push(50), "full buffer rejects push");

    const auto second = buffer.pop();
    const auto third = buffer.pop();
    const auto fourth = buffer.pop();
    expect(second && *second == 20, "FIFO second item");
    expect(third && *third == 30, "FIFO third item");
    expect(fourth && *fourth == 40, "FIFO wrapped item");
    expect(!buffer.pop().has_value(), "empty buffer returns nullopt");

    if (failures == 0) {
        std::cout << "PASS ring buffer\n";
    }
    return failures == 0 ? 0 : 1;
}

