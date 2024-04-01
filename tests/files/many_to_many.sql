CREATE TABLE Parent
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `code` VARCHAR(36) NOT NULL,
    `children` List<String> __assoc Child.code,
    PRIMARY KEY (`id`)
);


CREATE TABLE Child
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `code` VARCHAR(36) NOT NULL,
    `parents` List<String> __assoc Parent.code,
    PRIMARY KEY (`id`)
);
