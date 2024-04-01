--
CREATE TABLE `Child`
(
    `id` INT AUTO_INCREMENT NOT NULL,
    PRIMARY KEY (id)
);


--
CREATE TABLE `Parent`
(
    `id` INT AUTO_INCREMENT NOT NULL,
    PRIMARY KEY (id)
);


-- Generated from template table 'Child', for Parent.children
CREATE TABLE `Parent_children`
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `Parent_id` int NULL COMMENT '外键，指向Parent（）',
    PRIMARY KEY (id),
    FOREIGN KEY children (Parent_id) REFERENCES Parent (id)
);
