// What stays on this device: the patch and the ring in localStorage, loops (their WAV and their notes) in
// IndexedDB. Every name starts with "pad-synth:" so apps served from one address never share a key.

const PREFIX = "pad-synth:";
const STATE_KEY = `${PREFIX}state`;
const DB_NAME = `${PREFIX}loops`;
const STORE = "loops";

export function loadState() {
  try {
    const text = localStorage.getItem(STATE_KEY);
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

export function saveState(state) {
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
  } catch {
    // A full or blocked storage keeps the session's state in memory only.
  }
}

let opening = null;

function open() {
  if (!("indexedDB" in window)) return Promise.reject(new Error("no IndexedDB"));
  opening =
    opening ||
    new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  return opening;
}

function run(mode, work) {
  return open().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const request = work(tx.objectStore(STORE));
        tx.oncomplete = () => resolve(request ? request.result : undefined);
        tx.onerror = () => reject(tx.error);
      }),
  );
}

export const loops = {
  all: () => run("readonly", (store) => store.getAll()).then((list) => list.sort((a, b) => a.created - b.created)),
  put: (loop) => run("readwrite", (store) => store.put(loop)),
  remove: (id) => run("readwrite", (store) => store.delete(id)),
};

/** Saves `blob` as a file named `name` through the browser's download. */
export function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}
