// The computer opponent, off the main thread: { id, fen, strength } in, { id, move } out.
import { bestMove } from "./search.js";

self.onmessage = (event) => {
  const { id, fen, strength } = event.data;
  const move = bestMove(fen, strength, { timeMs: 1800 });
  self.postMessage({ id, move });
};
