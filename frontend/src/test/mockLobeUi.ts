import React from "react";

export const Center = ({ children, style, ...props }: any) => {
  return React.createElement("div", {
    style: { display: "flex", alignItems: "center", justifyContent: "center", ...style },
    ...props
  }, children);
};

export const Icon = ({ icon, size, color, ...props }: any) => {
  return React.createElement("span", {
    style: { display: "inline-flex", width: size, height: size, color },
    ...props
  }, "🔗");
};

export const ProviderIcon = () => "🔗";

export const theme = {
  getDesignToken: () => ({
    colorTextDescription: "",
    colorFillSecondary: "",
  }),
  darkAlgorithm: {},
  defaultAlgorithm: {}
};

export const ConfigProvider = ({ children }: any) => children;

export const Tag = ({ children }: any) => children;

export const message = {
  useMessage: () => [{}, null]
};

export const notification = {
  useNotification: () => [{}, null]
};

export const Modal = {
  useModal: () => [{}, null]
};

export const Grid = {
  useBreakpoint: () => ({})
};

export const version = "5.0.0";

export const Divider = () => null;

export const Flexbox = ({ children, style, ...props }: any) => {
  return React.createElement("div", {
    style: { display: "flex", ...style },
    ...props
  }, children);
};



