#include "student_average.h"

double student_average(const Student *student)
{
    if (!student) {
        return 0.0;
    }
    return ((double)student->scores[0] + student->scores[1] + student->scores[2]) / 3.0;
}
