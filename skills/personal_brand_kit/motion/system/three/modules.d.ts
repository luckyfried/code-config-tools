declare module 'opentype.js';

// The page's font set is a set of faces: `document.fonts.add` is typed with the DOM's iterable half.
interface FontFaceSet extends Set<FontFace> {}
