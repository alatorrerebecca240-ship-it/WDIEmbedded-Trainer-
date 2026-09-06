// MIT: self-authored image check; exercise source is never part of the image.
#include <boost/date_time/posix_time/posix_time.hpp>
int main() {
    const boost::posix_time::ptime start(boost::gregorian::date(2020, 1, 1));
    const auto end = start + boost::posix_time::seconds(1000000000);
    return (end - start).total_seconds() == 1000000000 ? 0 : 1;
}
