USE library;

INSERT INTO AUTHOR (name, country) VALUES 
('Naguib Mahfouz', 'Egypt'),
('Agatha Christie', 'UK'),
('George Orwell', 'UK');

INSERT INTO BOOK (title, price, author_id) VALUES 
('Palace Walk', 15.99, 1),
('Sugar Street', 14.50, 1),
('Murder on the Orient Express', 12.00, 2),
('And Then There Were None', 11.50, 2),
('1984', 13.99, 3),
('Animal Farm', 9.99, 3);