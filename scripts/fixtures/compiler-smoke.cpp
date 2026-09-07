#include <boost/date_time/posix_time/posix_time.hpp>
#include <iostream>
#include <string>
#include <vector>

int main() {
    const std::vector<int> values{2, 3};
    const std::string text = "ok";
    const boost::posix_time::ptime start(boost::gregorian::date(2026, 1, 1));
    const auto later = start + boost::posix_time::seconds(1);
    std::cout << "C++17 and Boost environment smoke test\n";
    return values[0] + values[1] == 5 && text.size() == 2 && later > start ? 0 : 1;
}
