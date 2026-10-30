// The moves, cuts, and closers the style cards name, each built once in its own file and exported here by the name the
// cards use. A kit's own move, cut, or closer registers beside them under a name of its own with `register`, and a
// board names it the same way it names a shared one.
import anamorphicPushMove from './move/anamorphic-push';
import barsOpenMove from './move/bars-open';
import breathHoldMove from './move/breath-hold';
import cellRevealMove from './move/cell-reveal';
import cropShiftMove from './move/crop-shift';
import dateStampMove from './move/date-stamp';
import diptychMove from './move/diptych';
import doodleDrawOnMove from './move/doodle-draw-on';
import gateWeaveMove from './move/gate-weave';
import gridSnapMove from './move/grid-snap';
import lateralDollyMove from './move/lateral-dolly';
import lightLeakMove from './move/light-leak';
import lineByLineTypeRiseMove from './move/line-by-line-type-rise';
import longFadeTitleMove from './move/long-fade-title';
import marqueeMove from './move/marquee';
import matchCutMove from './move/match-cut';
import pageDriftMove from './move/page-drift';
import polaroidDropMove from './move/polaroid-drop';
import rollBurnMove from './move/roll-burn';
import ruleDrawMove from './move/rule-draw';
import scaleToCellMove from './move/scale-to-cell';
import slowPushMove from './move/slow-push';
import stackAndSplitMove from './move/stack-and-split';
import stickerPopMove from './move/sticker-pop';
import tapeSlapMove from './move/tape-slap';
import typeMaskRevealMove from './move/type-mask-reveal';
import whiteSpaceCropMove from './move/white-space-crop';
import widthStretchMove from './move/width-stretch';
import wordPerBeatSlamMove from './move/word-per-beat-slam';
import zoomRockerMove from './move/zoom-rocker';
import barsCloseCut from './cut/bars-close';
import dissolveCut from './cut/dissolve';
import flashFrameCut from './cut/flash-frame';
import gridWipeCut from './cut/grid-wipe';
import hardCutCut from './cut/hard-cut';
import longDissolveCut from './cut/long-dissolve';
import longFadeCut from './cut/long-fade';
import pageTurnCut from './cut/page-turn';
import paperSlideCut from './cut/paper-slide';
import rollBurnCut from './cut/roll-burn';
import slideCut from './cut/slide';
import bookCoverCloser from './closer/book-cover';
import captionAloneCloser from './closer/caption-alone';
import closingFlickerCloser from './closer/closing-flicker';
import letterBuildCloser from './closer/letter-build';
import posterCloser from './closer/poster';
import titleCardCloser from './closer/title-card';
import counterMove from './move/counter';
import explodedLayersMove from './move/exploded-layers';
import pictureTunnelMove from './move/picture-tunnel';
import slamWordsMove from './move/slam-words';
import tiltedWallMove from './move/tilted-wall';
import type {CloserShape, Cut, Move} from './types';

export type {BeatOn, CloserProps, CloserShape, Cut, CutProps, Grid, Look, Move, MoveProps, Nudge, Tones} from './types';

export const MOVES: Record<string, Move> = {
  'anamorphic-push': anamorphicPushMove,
  'bars-open': barsOpenMove,
  'breath-hold': breathHoldMove,
  'cell-reveal': cellRevealMove,
  'crop-shift': cropShiftMove,
  'date-stamp': dateStampMove,
  'diptych': diptychMove,
  'doodle-draw-on': doodleDrawOnMove,
  'gate-weave': gateWeaveMove,
  'grid-snap': gridSnapMove,
  'lateral-dolly': lateralDollyMove,
  'light-leak': lightLeakMove,
  'line-by-line-type-rise': lineByLineTypeRiseMove,
  'long-fade-title': longFadeTitleMove,
  'marquee': marqueeMove,
  'match-cut': matchCutMove,
  'page-drift': pageDriftMove,
  'polaroid-drop': polaroidDropMove,
  'roll-burn': rollBurnMove,
  'rule-draw': ruleDrawMove,
  'scale-to-cell': scaleToCellMove,
  'slow-push': slowPushMove,
  'stack-and-split': stackAndSplitMove,
  'sticker-pop': stickerPopMove,
  'tape-slap': tapeSlapMove,
  'type-mask-reveal': typeMaskRevealMove,
  'white-space-crop': whiteSpaceCropMove,
  'width-stretch': widthStretchMove,
  'word-per-beat-slam': wordPerBeatSlamMove,
  'zoom-rocker': zoomRockerMove,
  'exploded-layers': explodedLayersMove,
  'picture-tunnel': pictureTunnelMove,
  'tilted-wall': tiltedWallMove,
  'slam-words': slamWordsMove,
  'counter': counterMove,
};

export const TRANSITIONS: Record<string, Cut> = {
  'bars-close': barsCloseCut,
  'dissolve': dissolveCut,
  'flash-frame': flashFrameCut,
  'grid-wipe': gridWipeCut,
  'hard-cut': hardCutCut,
  'long-dissolve': longDissolveCut,
  'long-fade': longFadeCut,
  'page-turn': pageTurnCut,
  'paper-slide': paperSlideCut,
  'roll-burn': rollBurnCut,
  'slide': slideCut,
};

export const CLOSERS: Record<string, CloserShape> = {
  'book-cover': bookCoverCloser,
  'caption-alone': captionAloneCloser,
  'closing-flicker': closingFlickerCloser,
  'letter-build': letterBuildCloser,
  'poster': posterCloser,
  'title-card': titleCardCloser,
};

/** Adds a kit's own move, cut, or closer under its name. A name the shared set already has is refused, so a kit never
 * changes what a card's name means. */
export const register = (kind: 'move' | 'transition' | 'closer', name: string, thing: Move | Cut | CloserShape) => {
  const table = (kind === 'move' ? MOVES : kind === 'transition' ? TRANSITIONS : CLOSERS) as Record<string, unknown>;
  if (name in table) throw new Error(`MOVE_ERROR ${kind} ${name} is already named`);
  table[name] = thing;
};

/** The move, cut, or closer a board names; a name nothing registered is an error, never a silent default. */
export const moveOf = (name?: string) => {
  if (!name) return undefined;
  const m = MOVES[name];
  if (!m) throw new Error(`MOVE_ERROR no move named ${name}`);
  return m;
};
export const cutOf = (name?: string | null) => {
  if (!name) return undefined;
  const c = TRANSITIONS[name];
  if (!c) throw new Error(`MOVE_ERROR no transition named ${name}`);
  return c;
};
export const closerOf = (name?: string) => {
  if (!name) return undefined;
  const c = CLOSERS[name];
  if (!c) throw new Error(`MOVE_ERROR no closer named ${name}`);
  return c;
};
