/**
 * Sample questions configuration for different tasks
 * 
 * This file contains sample questions for each task type (chat, arguments, statement, document)
 * To update questions, simply edit the arrays below for the respective task.
 */

// Questions for general chat
export const chatQuestions = [
  "What is SAT decision in WA, Australia?",
  "How do I file a claim with SAT for a rental dispute?",
  "Show me cases about disability discrimination in the workplace"
];

// Questions for build arguments task
export const argumentsQuestions = [
  `Please click the + button below to upload the case detail file or copy paste case detail in the text box below.
  `
];

// Questions for statement task
export const statementQuestions = [
  "Help me draft a statement for a rental bond dispute",
  "What should I include in my statement about workplace discrimination?",
  "How do I structure a statement for unfair dismissal?",
  "What evidence should I prepare for a contract dispute hearing?"];

// Questions for document task
export const documentQuestions = [
  "What documents do I need to file a claim with SAT?",
  "How should I organize evidence for my rental dispute case?",
  "What format should legal exhibits be in for SAT proceedings?",
  "Show me examples of successful SAT application documents"
];

// Get questions based on task type
export const getQuestionsByTask = (taskType) => {
  switch (taskType) {
    case "chat":
      return chatQuestions;
    case "arguments":
      return argumentsQuestions;
    case "statement":
      return statementQuestions;
    case "document":
      return documentQuestions;
    default:
      return chatQuestions;
  }
};

export default getQuestionsByTask;