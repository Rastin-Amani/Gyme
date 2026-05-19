import { Printer } from "prettier";
import { BlockNode, Node } from "./jinja";
export declare const getVisitorKeys: (ast: Node | {
    [id: string]: Node;
}) => string[];
export declare const print: Printer<Node>["print"];
export declare const embed: Printer<Node>["embed"];
/**
 * Returns the indexs of the first and the last character of any placeholder
 * occuring in a string.
 */
export declare const findPlaceholders: (text: string) => [number, number][];
export declare const surroundingBlock: (node: Node) => BlockNode | undefined;
