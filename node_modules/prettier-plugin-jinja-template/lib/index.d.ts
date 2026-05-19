import { Node } from "./jinja";
import { Parser, Printer, SupportLanguage } from "prettier";
export declare const languages: SupportLanguage[];
export declare const parsers: {
    "jinja-template": Parser<Node>;
};
export declare const printers: {
    "jinja-template": Printer<Node>;
};
