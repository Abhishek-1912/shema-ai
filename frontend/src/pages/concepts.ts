import type { Concept } from './ConceptPage'

// Text for the tabs we have not built yet. Plain data, kept out of the components.

export const mcpConcept: Concept = {
  title: 'MCP',
  module: 'Module 05',
  summary:
    'Model Context Protocol: a standard way to give the AI tools, so it can look things up and take actions instead of only writing text.',
  points: [
    'An MCP server offers tools, for example "search the database" or "find a document".',
    'The AI reads the list of tools and decides when one would help answer your question.',
    'Our backend runs the tool and sends the result back to the AI, which then answers.',
    'Dangerous actions need your permission first.',
  ],
}

export const wikiConcept: Concept = {
  title: 'LLM Wiki',
  module: 'Module 06',
  summary:
    'A knowledge base of articles that the AI helps write and keep up to date, and that it can search and cite.',
  points: [
    'Knowledge is stored as Markdown articles, each with its sources.',
    'Articles link to each other (relationships), forming a small knowledge graph.',
    'The AI can draft new articles from your documents; you review and approve them.',
    'Every change is versioned, so you can see who changed what and go back.',
  ],
}
