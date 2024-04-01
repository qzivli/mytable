CREATE TABLE Parent
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `children` List<Child>,
    PRIMARY KEY (`id`)
);

CREATE TABLE Child
(
    `id` INT AUTO_INCREMENT NOT NULL,
    PRIMARY KEY (`id`)
);