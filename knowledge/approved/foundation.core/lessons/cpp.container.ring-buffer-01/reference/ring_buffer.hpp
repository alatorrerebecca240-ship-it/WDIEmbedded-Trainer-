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
        if (full()) {
            return false;
        }
        data_[write_index_] = value;
        write_index_ = (write_index_ + 1U) % Capacity;
        ++size_;
        return true;
    }

    std::optional<T> pop()
    {
        if (empty()) {
            return std::nullopt;
        }
        T value = data_[read_index_];
        read_index_ = (read_index_ + 1U) % Capacity;
        --size_;
        return value;
    }

    std::size_t size() const { return size_; }
    bool empty() const { return size_ == 0U; }
    bool full() const { return size_ == Capacity; }

private:
    std::array<T, Capacity> data_{};
    std::size_t read_index_{0};
    std::size_t write_index_{0};
    std::size_t size_{0};
};

#endif
