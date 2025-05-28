"""
LLM Providers Module

This module handles the integration with different LLM providers.
"""
import logging
from typing import List, Dict, Any, Optional, Union, Generator, Callable
from abc import ABC, abstractmethod
import json
from app.config import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments for the LLM
            
        Returns:
            str: The generated completion
        """
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str, callback: Callable[[str], None], **kwargs) -> None:
        """
        Generate a streaming completion for the given prompt.
        
        Args:
            prompt: The prompt to complete
            callback: Function to call with each chunk of the response
            **kwargs: Additional arguments for the LLM
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name
        """
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the OpenAI provider.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        try:
            api_key = settings.OPENAI_API_KEY
            self.client = OpenAI(api_key=api_key)
            self.model_name = model_name
            logger.info(f"Initialized OpenAI provider with model: {model_name}")
        except ImportError:
            logger.error("Failed to import OpenAI. Make sure openai package is installed.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion using OpenAI.
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments for the OpenAI API
            
        Returns:
            str: The generated completion
        """
        try:
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            tools = kwargs.get("tools")
            response_format = kwargs.get("response_format")

            # Prepare base request
            request_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "developer", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Optional: Add reasoning_effort for o3 models
            if self.model_name.startswith("o3"):
                request_params["reasoning_effort"] = kwargs.get("reasoning_effort", "medium")

            # Optional: tools or functions
            if tools:
                request_params["tools"] = tools
            if response_format:
                request_params["response_format"] = response_format

            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating completion with OpenAI: {e}")
            return f"Error generating response: {str(e)}"
        
    def generate_streaming(self, prompt: str, callback: Callable[[str], None], **kwargs) -> None:
        """
        Generate a streaming completion using OpenAI.
        
        Args:
            prompt: The prompt to complete
            callback: Function to call with each chunk of the response
            **kwargs: Additional arguments for the OpenAI API
        """
        try:
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    callback(chunk.choices[0].delta.content)
        except Exception as e:
            logger.error(f"Error streaming completion with OpenAI: {e}")
            callback(f"\nError generating response: {str(e)}")
    
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name
        """
        return f"openai/{self.model_name}"

class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider."""
    
    def __init__(self, model_name: str = "deepseek-reasoner"):
        """
        Initialize the DeepSeek provider.
        
        Args:
            model_name: Name of the DeepSeek model to use
        """
        try:
            # Create client with minimal parameters to avoid proxies issues
            from openai import OpenAI
            self.client = None  # Initialize to None first
            
            # Create a new instance directly with only required parameters
            api_key = settings.DEEPSEEK_API_KEY
            base_url = "https://api.deepseek.com/v1"
            
            # Method 1: Direct instantiation with minimal parameters
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            self.model_name = model_name
            logger.info(f"Initialized DeepSeek provider with model: {model_name}")
        except ImportError:
            logger.error("Failed to import OpenAI. Make sure openai package is installed.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {e}")
            raise
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion using DeepSeek.
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments for the DeepSeek API
            
        Returns:
            str: The generated completion
        """
        try:
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Check if response is None before accessing attributes
            if response is None:
                logger.error("Received None response from DeepSeek API")
                return "Error: Failed to get a response from DeepSeek API. Please try again with OpenAI provider."
                
            # Check if response has the expected structure
            if not hasattr(response, 'choices') or not response.choices:
                logger.error(f"Invalid response structure from DeepSeek: {response}")
                return "Error: Received invalid response structure from DeepSeek API. Please try again with OpenAI provider."
                
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating completion with DeepSeek: {e}")
            # Return a more specific error message for easier debugging
            return f"Error generating response from DeepSeek: {str(e)}. Please try again with OpenAI provider or check your API key."
    
    def generate_streaming(self, prompt: str, callback: Callable[[str], None], **kwargs) -> None:
        """
        Generate a streaming completion using DeepSeek.
        
        Args:
            prompt: The prompt to complete
            callback: Function to call with each chunk of the response
            **kwargs: Additional arguments for the DeepSeek API
        """
        try:
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Check if stream is None
            if stream is None:
                error_msg = "Received None stream from DeepSeek API"
                logger.error(error_msg)
                callback(f"\nError: {error_msg}. Please try again with OpenAI provider.")
                return
                
            for chunk in stream:
                # Add defensive checks for each chunk
                if chunk is None or not hasattr(chunk, 'choices') or not chunk.choices:
                    continue
                    
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content:
                    callback(chunk.choices[0].delta.content)
                    
        except Exception as e:
            logger.error(f"Error streaming completion with DeepSeek: {e}")
            callback(f"\nError generating response from DeepSeek: {str(e)}. Please try again with OpenAI provider or check your API key.")
    
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name
        """
        return f"deepseek/{self.model_name}"

class AnthropicProvider(LLMProvider):
    """
    Provider for Anthropic Claude models.
    """
    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.model_name = model_name
        except ImportError:
            logger.error("Anthropic package is not installed. Please install it with 'pip install anthropic'.")
            raise
        except Exception as e:
            logger.error(f"Error initializing Anthropic provider: {e}")
            raise
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a completion using the Anthropic API.
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments to pass to the API
        
        Returns:
            str: The generated text
        """
        try:
            # Log model details at generation time
            logger.info(f"[MODEL GENERATION] Anthropic generating with model: {self.model_name}")
            print(f"[MODEL GENERATION] Anthropic generating with model: {self.model_name}")
            
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            
            # Create the completion
            response = self.client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error generating completion with Anthropic: {e}")
            return f"Error generating completion: {str(e)}"
    
    def generate_streaming(self, prompt: str, callback: Callable[[str], None], **kwargs) -> None:
        """
        Generate a streaming completion using the Anthropic API.
        
        Args:
            prompt: The prompt to complete
            callback: Function to call with each chunk of the response
            **kwargs: Additional arguments for the API
        """
        try:
            temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
            max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)
            
            # Create the streaming completion with Anthropic's streaming API
            with self.client.messages.stream(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        callback(text)
            
        except Exception as e:
            logger.error(f"Error generating streaming completion with Anthropic: {e}")
            callback(f"Error generating streaming response: {str(e)}")
    
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name
        """
        return self.model_name

class DummyProvider(LLMProvider):
    """Dummy LLM provider for testing."""
    
    def __init__(self, model_name: str = "dummy"):
        """
        Initialize the dummy provider.
        
        Args:
            model_name: Name of the dummy model
        """
        self.model_name = model_name
        logger.info(f"Initialized Dummy provider with model: {model_name}")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a dummy completion.
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments (ignored)
            
        Returns:
            str: The dummy completion
        """
        # Create a simple response based on the prompt to simulate LLM behavior
        prompt_preview = prompt[:50] + ("..." if len(prompt) > 50 else "")
        return f"This is a dummy response to: '{prompt_preview}'"
    
    def generate_streaming(self, prompt: str, callback: Callable[[str], None], **kwargs) -> None:
        """
        Generate a dummy streaming completion.
        
        Args:
            prompt: The prompt to complete
            callback: Function to call with each chunk of the response
            **kwargs: Additional arguments (ignored)
        """
        import time
        
        # Split response into chunks with small delays to simulate streaming
        response = self.generate(prompt)
        chunks = [response[i:i+10] for i in range(0, len(response), 10)]
        
        for chunk in chunks:
            callback(chunk)
            time.sleep(0.1)
    
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.
        
        Returns:
            str: Provider name
        """
        return f"dummy/{self.model_name}"

def get_llm_provider(provider: str = None, model: str = None, for_chat: bool = True) -> LLMProvider:
    """
    Get an LLM provider instance based on configuration.
    
    Args:
        provider: Provider name (openai, deepseek, anthropic)
        model: Model name
        for_chat: Whether this is for the chat feature (True) or arguments feature (False)
        
    Returns:
        LLMProvider: An instance of the appropriate LLM provider
    """
    # Use provided values or defaults from settings
    if provider is None:
        provider = settings.CHAT_LLM_PROVIDER if for_chat else settings.ARGUMENTS_LLM_PROVIDER
    
    if model is None:
        model = settings.CHAT_LLM_MODEL if for_chat else settings.ARGUMENTS_LLM_MODEL
    
    # # Map specific model names if needed
    # if model == "deepseek-reasoner":
    #     model = "o4-mini"
    #     provider = "openai"  # Explicitly set the provider to OpenAI
    
    # Detect provider from model name if not explicitly provided
    if model and model.startswith('claude-'):
        provider = 'anthropic'
    elif model and (model.startswith('gpt-') or model == 'text-davinci-003'):
        provider = 'openai'
    elif model and model.startswith('deepseek-'):
        provider = 'deepseek'
    
    # Detailed logging for debugging model selection
    request_type = "Chat" if for_chat else "Arguments"
    logger.info(f"[MODEL DETAILS] Request type: {request_type}")
    logger.info(f"[MODEL DETAILS] Selected provider: {provider}")
    logger.info(f"[MODEL DETAILS] Selected model: {model}")
    
    # Print to console for immediate visibility during development
    print(f"[MODEL DETAILS] Request type: {request_type}")
    print(f"[MODEL DETAILS] Selected provider: {provider}")
    print(f"[MODEL DETAILS] Selected model: {model}")
    
    # Return the appropriate provider
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIProvider(model_name=model)
    elif provider == "deepseek":
        return DeepSeekProvider(model_name=model)
    elif provider == "anthropic":
        return AnthropicProvider(model_name=model)
    else:
        # Fallback to dummy provider
        logger.warning(f"Unknown provider '{provider}'. Using dummy provider.")
        return DummyProvider(model_name="dummy") 