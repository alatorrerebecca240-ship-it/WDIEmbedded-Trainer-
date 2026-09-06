#ifndef TRAINER_RING_BUFFER_HPP
#define TRAINER_RING_BUFFER_HPP

#include <array>
#include <cstddef>
#include <optional>

template <typename T, std::size_t Capacity>
class RingBuffer {
    static_assert(Capacity > 0, "Capacity must be greater than zero");

public:
    bool push(const T &value)
    {
        /* TODO: 写入 value，并在成功时更新索引和数量。 */
        (void)value;
        return false;
    }

    std::optional<T> pop()
    {
        /* TODO: 读取最早写入的元素。 */
        return std::nullopt;
    }

    std::size_t size() const { return 0; /* TODO */ }
    bool empty() const { return true; /* TODO */ }
    bool full() const { return false; /* TODO */ }

private:
    std::array<T, Capacity> data_{};
    std::size_t read_index_{0};
    std::size_t write_index_{0};
    std::size_t size_{0};
};

#endif

