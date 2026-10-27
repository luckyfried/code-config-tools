// Runs the computer's search off the page's thread: { id, board, color, strength } in, { id, square, score } out.
import { chooseMove } from "./engine.js";

self.addEventListener("message", (event) => {
  const { id, board, color, strength } = event.data;
  const result = chooseMove(board, color, strength, { random: Math.random });
  self.postMessage({ id, square: result.square, score: result.score });
});
