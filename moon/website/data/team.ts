// Founders and leadership for the About page.
// Source: founders whiteboard (Oct 2026). Only facts from that board are used here;
// Photos: Saurabh and Manish supplied by the team; Devansh and Karol from their official Instagram accounts;
// Shashwat from his official YouTube channel;
// people without a photo show their initials until a headshot is supplied.

export type Person = {
  name: string;
  role: string;
  initials: string;
  bio: string;
  tags: string[];
  photo?: string;
  links?: { x?: string; linkedin?: string; youtube?: string };
};

export const cofounders: Person[] = [
  {
    name: "Saurabh Maurya",
    role: "Co-founder & CTO",
    initials: "SM",
    bio: "Engineer and serial founder. Saurabh studied at IIT (BHU), built Ranker, Oitetra and iitanmacro.ai, and backs early-stage startups as an angel investor. He leads technology at Moon Exchange.",
    tags: ["IIT (BHU)", "Founder of 3 ventures", "Angel investor"],
    photo: "/team/saurabh.webp",
  },
  {
    name: "Neha Jareda",
    role: "Co-founder",
    initials: "NJ",
    bio: "An IIT Kharagpur graduate who owns and runs several fintech businesses. Neha brings an operator's sense of how financial products are built, launched and scaled.",
    tags: ["IIT Kharagpur", "Fintech entrepreneur"],
  },
  {
    name: "CA Manish Singh",
    role: "Co-founder & CFO",
    initials: "MS",
    bio: "A Chartered Accountant with 15+ years trading equities and derivatives. Manish has worked with ITC, TCS and MCX, and is a founding member of FinGrad and Trade Brains. He runs finance at Moon Exchange.",
    tags: ["Chartered Accountant", "15+ years in markets", "ITC · TCS · MCX"],
    photo: "/team/manish-blazer.webp",
  },
  {
    name: "Devansh Rai",
    role: "Co-founder",
    initials: "DR",
    bio: "Devansh has made finance content for over 10 years and reaches 1M+ followers across social platforms, explaining markets, business and the lessons from his own journey.",
    tags: ["Finance creator", "10+ years", "1M+ followers"],
    photo: "/team/devansh-yacht.webp",
  },
];

export const leadership: Person[] = [
  {
    name: "Buddhiprakash Karol",
    role: "Chief Marketing Officer",
    initials: "BK",
    bio: "An IIT Kharagpur graduate who built a chain of hotels across India, then turned to the markets. Karol is a SEBI-registered research analyst and leads marketing.",
    tags: ["IIT Kharagpur", "SEBI-registered RA"],
    photo: "/team/karol.webp",
  },
  {
    name: "Shashwat Amrev",
    role: "Chief Operating Officer",
    initials: "SA",
    bio: "Entrepreneur, author and investor. Shashwat founded AmrevX and Stock Market Edges, wrote Stonks from Scratch and was named an Economic Times Leader of Change. He runs operations.",
    tags: ["Founder, AmrevX", "Author", "ET Leaders of Change"],
    photo: "/team/shashwat.webp",
  },
];

export const values = [
  {
    title: "One price for everyone",
    body: "Transparent fees, clear liquidation rules and identical execution, whether you trade ₹1,000 or ₹1 crore.",
  },
  {
    title: "Compliance before growth",
    body: "KYC, AML monitoring and FIU-IND registration were in the plan before the first line of code.",
  },
  {
    title: "Made for Indian traders",
    body: "Rupee deposits with no fee, support in Indian hours and products shaped by how India actually trades.",
  },
];
