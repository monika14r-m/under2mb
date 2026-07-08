// config.js
// Shared constants used across the app.

export const DEFAULT_LIMIT_MB = 2;

// Quality steps tried (in order) when compressing JPEGs before resizing.
export const JPEG_QUALITY_STEPS = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1];

// Scale factor applied per attempt when resolution has to be reduced.
export const RESIZE_SCALE_STEP = 0.9;

// Safety caps so a pathological image can't loop forever.
export const MAX_RESIZE_ATTEMPTS_JPEG = 12;
export const MAX_RESIZE_ATTEMPTS_PNG = 15;
export const MIN_DIMENSION_PX = 20;

export const ACCEPTED_EXTENSIONS = /\.(png|jpe?g)$/i;
export const ACCEPTED_MIME = /^image\/(png|jpeg)$/;
