#ifndef TRAINER_STUDENT_AVERAGE_H
#define TRAINER_STUDENT_AVERAGE_H

typedef struct {
    char name[16];
    int scores[3];
} Student;

double student_average(const Student *student);

#endif
