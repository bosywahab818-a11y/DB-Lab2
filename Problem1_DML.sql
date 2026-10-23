USE company;

-- Disable FK checks temporarily for initial mutual insertions
SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO DEPARTMENT VALUES 
(1, 'HR', 101, '2023-01-01'),
(2, 'IT', 102, '2023-02-01'),
(3, 'Finance', 103, '2023-03-01');

INSERT INTO EMPLOYEE VALUES 
(101, 'John', 'Doe', '1990-05-15', '123 Main St', 'M', 6000.00, 1),
(102, 'Jane', 'Smith', '1992-08-20', '456 Oak St', 'F', 7500.00, 2),
(103, 'Ali', 'Hassan', '1988-11-10', '789 Pine St', 'M', 8000.00, 3);

INSERT INTO PROJECT VALUES 
(10, 'Web Redesign', 'Cairo', 2),
(20, 'ERP System', 'Alexandria', 3),
(30, 'Recruitment Drive', 'Giza', 1);

SET FOREIGN_KEY_CHECKS = 1;