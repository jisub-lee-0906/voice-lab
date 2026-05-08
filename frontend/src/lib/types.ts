export type Candidate = {
  index: number;
  seed: number;
  wav: string;
  ogg: string;
  url: string;
};

export type GenerateResponse = {
  message: string;
  candidates: Candidate[];
  warnings?: string[];
};

export type ReferenceResponse = {
  path: string;
  url: string;
  duration: number;
  emotion: string;
  message: string;
};
